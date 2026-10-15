"""The Keycloak signing keys the library trusts (rule BR1.4).

Keys are fetched when the service starts and refreshed only when a token names a key id we do
not hold, at most once a minute. A failed refresh keeps every key already held (state ``stale``);
a failed first fetch leaves the set empty.
"""

from __future__ import annotations

import enum
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx
import jwt

log = logging.getLogger("modelhub.keys")

REFRESH_INTERVAL_SECONDS = 60
ALLOWED_ALGORITHMS = ("RS256", "ES256")


class KeyState(enum.Enum):
    EMPTY = "empty"
    LOADED = "loaded"
    STALE = "stale"


@dataclass(frozen=True)
class SigningKey:
    kid: str
    algorithm: str
    key: object


def _algorithm_for(jwk: dict) -> str | None:
    kty = jwk.get("kty")
    if kty == "RSA":
        return "RS256"
    if kty == "EC":
        return "ES256"
    return None


def parse_jwks(document: dict) -> dict[str, SigningKey]:
    keys: dict[str, SigningKey] = {}
    for jwk in document.get("keys", []):
        kid = jwk.get("kid")
        algorithm = _algorithm_for(jwk)
        if not kid or algorithm is None or jwk.get("use", "sig") != "sig":
            continue
        try:
            keys[kid] = SigningKey(kid, algorithm, jwt.PyJWK(jwk).key)
        except (jwt.PyJWKError, ValueError):
            log.warning("ignored an unusable signing key", extra={"event": "key_ignored"})
    return keys


def http_fetcher(url: str, connect: float = 5, read: float = 30) -> Callable[[], dict]:
    """A fetcher that reads the realm's published key set over HTTP."""

    def fetch() -> dict:
        timeout = httpx.Timeout(read, connect=connect)
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()

    return fetch


class KeySet:
    def __init__(
        self,
        fetch: Callable[[], dict],
        clock: Callable[[], float] = time.monotonic,
        refresh_interval: float = REFRESH_INTERVAL_SECONDS,
    ) -> None:
        self._fetch = fetch
        self._clock = clock
        self._interval = refresh_interval
        self._keys: dict[str, SigningKey] = {}
        self._state = KeyState.EMPTY
        self._last_attempt: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> KeyState:
        return self._state

    def load(self) -> None:
        """Fetch the keys now (service start-up)."""
        with self._lock:
            self._refresh(limited=False)

    def get(self, kid: str) -> SigningKey | None:
        key = self._keys.get(kid)
        if key is not None:
            return key
        with self._lock:
            key = self._keys.get(kid)
            if key is not None:
                return key
            now = self._clock()
            if self._last_attempt is None or now - self._last_attempt >= self._interval:
                self._refresh()
            return self._keys.get(kid)

    def _refresh(self, limited: bool = True) -> None:
        # The start-up fetch does not count against the one-a-minute limit on refreshes.
        if limited:
            self._last_attempt = self._clock()
        try:
            fresh = parse_jwks(self._fetch())
        except Exception as exc:  # noqa: BLE001 - any failure keeps the keys already held
            if self._keys:
                self._state = KeyState.STALE
            log.warning("signing key refresh failed", extra={"event": "key_refresh_failed"})
            del exc
            return
        if fresh:
            self._keys = fresh
            self._state = KeyState.LOADED
