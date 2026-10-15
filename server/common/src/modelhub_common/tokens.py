"""The token check (rules BR1.1, BR1.2, BR1.3).

A token is accepted only if its signing method, signature, issuer, audience, times and required
claims are all right. The verdict carries a fixed reason code for the log and never any part of
the token.
"""

from __future__ import annotations

import enum
import time
from collections.abc import Callable
from dataclasses import dataclass

import jwt

from .keys import ALLOWED_ALGORITHMS, KeySet

ADMIN_ROLE = "modelhub-admin"
LEEWAY_SECONDS = 60


class Reason(enum.Enum):
    OK = "ok"
    MISSING = "missing"
    MALFORMED = "malformed"
    BAD_SIGNATURE = "bad_signature"
    UNKNOWN_KEY = "unknown_key"
    EXPIRED = "expired"
    NOT_YET_VALID = "not_yet_valid"
    WRONG_ISSUER = "wrong_issuer"
    WRONG_AUDIENCE = "wrong_audience"
    MISSING_CLAIM = "missing_claim"
    BAD_ALGORITHM = "bad_algorithm"


@dataclass(frozen=True)
class Verdict:
    valid: bool
    reason: Reason
    person_id: str | None = None
    person_name: str | None = None
    is_admin: bool = False
    client_id: str | None = None


def _refuse(reason: Reason) -> Verdict:
    return Verdict(False, reason)


class TokenVerifier:
    def __init__(
        self,
        keys: KeySet,
        issuer: str,
        audience: str,
        leeway: int = LEEWAY_SECONDS,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._keys = keys
        self._issuer = issuer
        self._audience = audience
        self._leeway = leeway
        self._clock = clock

    def verify(self, token: str | None) -> Verdict:
        if not token:
            return _refuse(Reason.MISSING)
        if token.count(".") != 2:
            return _refuse(Reason.MALFORMED)
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError:
            return _refuse(Reason.MALFORMED)
        alg = header.get("alg")
        if alg not in ALLOWED_ALGORITHMS:
            return _refuse(Reason.BAD_ALGORITHM)
        key = self._keys.get(str(header.get("kid", "")))
        if key is None:
            return _refuse(Reason.UNKNOWN_KEY)
        if key.algorithm != alg:
            return _refuse(Reason.BAD_ALGORITHM)
        try:
            claims = jwt.decode(
                token,
                key.key,
                algorithms=[alg],
                options={
                    "verify_exp": False,
                    "verify_nbf": False,
                    "verify_iat": False,
                    "verify_aud": False,
                    "verify_iss": False,
                    "require": [],
                },
            )
        except jwt.InvalidSignatureError:
            return _refuse(Reason.BAD_SIGNATURE)
        except jwt.PyJWTError:
            return _refuse(Reason.MALFORMED)
        return self._check_claims(claims)

    def _check_claims(self, claims: dict) -> Verdict:
        if claims.get("iss") != self._issuer:
            return _refuse(Reason.WRONG_ISSUER)
        audience = claims.get("aud")
        audiences = audience if isinstance(audience, list) else [audience]
        if self._audience not in audiences:
            return _refuse(Reason.WRONG_AUDIENCE)
        exp = claims.get("exp")
        if not isinstance(exp, int | float):
            return _refuse(Reason.MISSING_CLAIM)
        now = self._clock()
        if exp < now - self._leeway:
            return _refuse(Reason.EXPIRED)
        nbf = claims.get("nbf")
        if isinstance(nbf, int | float) and nbf > now + self._leeway:
            return _refuse(Reason.NOT_YET_VALID)
        sub = claims.get("sub")
        name = claims.get("preferred_username")
        if not sub or not name:
            return _refuse(Reason.MISSING_CLAIM)
        roles = (claims.get("realm_access") or {}).get("roles") or []
        return Verdict(
            True,
            Reason.OK,
            person_id=str(sub),
            person_name=str(name),
            is_admin=ADMIN_ROLE in roles,
            client_id=claims.get("azp") if claims.get("client_id") else None,
        )
