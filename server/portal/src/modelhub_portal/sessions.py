"""Sessions kept in the portal's memory (rule BR1.2; NFR9.4).

The browser holds only a random id. The tokens never leave the server. A restart ends every
session, and so does eight idle hours (a setting).
"""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Session:
    id: str
    csrf: str
    access_token: str
    refresh_token: str | None
    access_expires: float
    person_id: str
    person_name: str
    is_admin: bool
    last_seen: float
    token_expired: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


class SessionStore:
    def __init__(self, idle_seconds: float = 8 * 3600, clock: Callable[[], float] = time.time):
        self._idle, self._clock = idle_seconds, clock
        self._items: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(
        self,
        access_token: str,
        refresh_token: str | None,
        access_expires: float,
        person_id: str,
        person_name: str,
        is_admin: bool,
    ) -> Session:
        session = Session(
            id=secrets.token_urlsafe(32),
            csrf=secrets.token_urlsafe(24),
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires=access_expires,
            person_id=person_id,
            person_name=person_name,
            is_admin=is_admin,
            last_seen=self._clock(),
        )
        with self._lock:
            self._items[session.id] = session
        return session

    def get(self, session_id: str | None) -> Session | None:
        """The live session, with its idle clock restarted; None when unknown or idle too long."""
        if not session_id:
            return None
        now = self._clock()
        with self._lock:
            session = self._items.get(session_id)
            if session is None:
                return None
            if now - session.last_seen > self._idle:
                del self._items[session_id]
                return None
            session.last_seen = now
            return session

    def delete(self, session_id: str | None) -> None:
        with self._lock:
            self._items.pop(session_id or "", None)

    def __len__(self) -> int:
        return len(self._items)
