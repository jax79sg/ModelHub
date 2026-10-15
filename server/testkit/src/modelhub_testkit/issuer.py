"""A fake Keycloak issuer for tests (BQ3).

It makes an RSA key, signs tokens with chosen claims and serves the key-set document, so the
shared token check and every service can be tested with valid, expired, tampered, wrong-audience,
wrong-algorithm and unknown-key tokens, and with no real Keycloak.
"""

from __future__ import annotations

import json
import time
import uuid

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

ADMIN_ROLE = "modelhub-admin"
SERVICE_CLIENT = "modelhub-artifactory-service"


class FakeIssuer:
    def __init__(
        self,
        issuer: str = "https://keycloak.test/realms/modelhub",
        audience: str = "modelhub",
    ) -> None:
        self.issuer = issuer
        self.audience = audience
        self._keys: list[tuple[str, rsa.RSAPrivateKey]] = []
        self._add_key()

    def _add_key(self) -> None:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self._keys.append((uuid.uuid4().hex[:12], key))

    def rotate(self) -> None:
        """Start signing with a new key; the old one stays in the key set."""
        self._add_key()

    def drop_old_keys(self) -> None:
        self._keys = self._keys[-1:]

    def jwks(self) -> dict:
        keys = []
        for kid, key in self._keys:
            jwk = json.loads(RSAAlgorithm.to_jwk(key.public_key()))
            jwk.update(kid=kid, use="sig", alg="RS256")
            keys.append(jwk)
        return {"keys": keys}

    def token(
        self,
        sub: str = "user-1",
        username: str = "user",
        admin: bool = False,
        roles: list[str] | None = None,
        expires_in: int = 300,
        audience: str | None = None,
        issuer: str | None = None,
        extra: dict | None = None,
        drop: tuple[str, ...] = (),
    ) -> str:
        now = int(time.time())
        all_roles = list(roles or [])
        if admin:
            all_roles.append(ADMIN_ROLE)
        claims = {
            "iss": issuer or self.issuer,
            "aud": audience or self.audience,
            "sub": sub,
            "preferred_username": username,
            "iat": now,
            "exp": now + expires_in,
            "realm_access": {"roles": all_roles},
        }
        claims.update(extra or {})
        for name in drop:
            claims.pop(name, None)
        kid, key = self._keys[-1]
        return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})

    def service_token(self, **kw) -> str:
        """A token for the import service's own client (client credentials)."""
        extra = {"azp": SERVICE_CLIENT, "client_id": SERVICE_CLIENT}
        extra.update(kw.pop("extra", {}))
        kw.setdefault("sub", "service-account-" + SERVICE_CLIENT)
        kw.setdefault("username", "service-account-" + SERVICE_CLIENT)
        return self.token(extra=extra, **kw)

    def hs256_token(self) -> str:
        """A token signed with a shared secret, which a verifier must refuse."""
        claims = {
            "iss": self.issuer,
            "aud": self.audience,
            "sub": "x",
            "exp": int(time.time()) + 300,
        }
        return jwt.encode(claims, "x" * 40, algorithm="HS256", headers={"kid": self._keys[-1][0]})
