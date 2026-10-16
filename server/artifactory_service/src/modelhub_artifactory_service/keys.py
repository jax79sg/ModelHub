"""The trusted signing keys (rule BR1.13; FR1.14, FR4.2).

Administrators manage the list. A key is added only when the typed fingerprint matches the key's
own, using the same check the CLI uses. A revoked key is refused from then on; imports already
done are not affected.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

import psycopg

from modelhub import signing


class InvalidKey(Exception):
    pass


class FingerprintMismatch(Exception):
    pass


class KeyExists(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _row(row: dict) -> dict:
    out = dict(row)
    for name in ("added_at", "revoked_at"):
        if out.get(name) is not None:
            out[name] = out[name].astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return out


class TrustedKeys:
    def __init__(self, pool, clock: Callable[[], datetime] = _utc_now) -> None:
        self._pool = pool
        self._clock = clock

    def add(
        self,
        public_key_text: str,
        typed_fingerprint: str,
        label: str,
        by_id: str,
        by_name: str,
    ) -> dict:
        label = (label or "").strip()
        if not 1 <= len(label) <= 80:
            raise InvalidKey("the label must be 1 to 80 characters")
        try:
            doc = signing.parse_public_doc(public_key_text)
        except signing.KeyError_ as exc:
            raise InvalidKey(str(exc)) from exc
        if not signing.fingerprints_match(typed_fingerprint, doc):
            raise FingerprintMismatch("the typed fingerprint does not match this key")
        try:
            with self._pool.connection() as conn:
                conn.execute(
                    "insert into trusted_keys (fingerprint, key_id, public_key, label, "
                    "added_by_id, added_by_name, added_at) values (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        doc["fingerprint"],
                        doc["key_id"],
                        doc["public_key"],
                        label,
                        by_id,
                        by_name,
                        self._clock(),
                    ),
                )
        except psycopg.errors.UniqueViolation as exc:
            raise KeyExists(doc["fingerprint"]) from exc
        return {"fingerprint": doc["fingerprint"], "key_id": doc["key_id"], "label": label}

    def list(self) -> list[dict]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "select fingerprint, key_id, label, added_by_name, added_at, revoked_at, "
                "revoked_by_name from trusted_keys order by added_at, fingerprint"
            ).fetchall()
        return [_row(r) for r in rows]

    def revoke(self, fingerprint: str, by_name: str) -> bool:
        """True when the key is known (a repeat is harmless); False when there is no such key."""
        with self._pool.connection() as conn, conn.transaction():
            row = conn.execute(
                "select revoked_at from trusted_keys where fingerprint = %s", (fingerprint,)
            ).fetchone()
            if row is None:
                return False
            if row["revoked_at"] is None:
                conn.execute(
                    "update trusted_keys set revoked_at = %s, revoked_by_name = %s "
                    "where fingerprint = %s",
                    (self._clock(), by_name, fingerprint),
                )
        return True

    def active_docs(self) -> list[dict]:
        """The public key documents the bundle check trusts (revoked keys left out)."""
        with self._pool.connection() as conn:
            rows = conn.execute(
                "select key_id, fingerprint, public_key from trusted_keys "
                "where revoked_at is null order by added_at"
            ).fetchall()
        return [dict(r) for r in rows]

    def find_active(self, fingerprint: str) -> dict | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "select key_id, fingerprint, public_key from trusted_keys "
                "where fingerprint = %s and revoked_at is null",
                (fingerprint,),
            ).fetchone()
        return dict(row) if row else None
