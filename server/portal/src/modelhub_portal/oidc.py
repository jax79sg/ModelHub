"""Sign-in with Keycloak: the authorisation code flow with a proof key (rule BR1.2; NFR5.3).

Authlib supplies the proof-key and address building; the calls to Keycloak are plain httpx so
they behave the same wherever the portal runs. The person's identity and role are read from the access token with
the shared token check, so the portal and the services agree on who is an administrator.
"""

from __future__ import annotations

import secrets
import threading
import time

import httpx
from authlib.oauth2.rfc6749.parameters import prepare_grant_uri
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from modelhub_common.keys import KeySet
from modelhub_common.tokens import TokenVerifier, Verdict


class AuthDown(Exception):
    """Keycloak could not be reached."""


class AuthRefused(Exception):
    """Keycloak refused the code or the refresh token."""


class Oidc:
    def __init__(
        self,
        issuer: str,
        client_id: str,
        client_secret,
        redirect_uri: str,
        verifier: TokenVerifier,
        keys: KeySet | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        self.issuer = issuer.rstrip("/")
        self._client_id = client_id
        self._secret = client_secret
        self._redirect = redirect_uri
        self._verifier = verifier
        self._keys = keys
        self._transport = transport
        self._timeout = timeout or httpx.Timeout(30, connect=5)
        self._meta: dict | None = None
        self._meta_at = 0.0
        self._lock = threading.Lock()

    def _secret_value(self) -> str:
        return self._secret() if callable(self._secret) else self._secret

    def _post(self, url: str, form: dict) -> dict:
        try:
            with httpx.Client(transport=self._transport, timeout=self._timeout) as http:
                r = http.post(url, data=form, auth=(self._client_id, self._secret_value()))
        except httpx.TransportError as exc:
            raise AuthDown("Keycloak could not be reached.") from exc
        if r.status_code >= 500:
            raise AuthDown("Keycloak could not be reached.")
        if r.status_code != 200:
            raise AuthRefused("Keycloak did not accept the request.")
        try:
            body = r.json()
        except ValueError as exc:
            raise AuthRefused("Keycloak answered with something unreadable.") from exc
        if not body.get("access_token"):
            raise AuthRefused("Keycloak gave no access token.")
        return body

    def metadata(self) -> dict:
        with self._lock:
            if self._meta is not None and time.time() - self._meta_at < 300:
                return self._meta
        try:
            with httpx.Client(transport=self._transport, timeout=self._timeout) as http:
                r = http.get(self.issuer + "/.well-known/openid-configuration")
            r.raise_for_status()
            meta = r.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AuthDown("Keycloak could not be reached.") from exc
        with self._lock:
            self._meta, self._meta_at = meta, time.time()
        return meta

    def start(self) -> tuple[str, str, str, str]:
        """(address to send the browser to, state, code verifier, nonce)."""
        meta = self.metadata()
        state = secrets.token_urlsafe(24)
        verifier = secrets.token_urlsafe(48)
        nonce = secrets.token_urlsafe(24)
        url = prepare_grant_uri(
            meta["authorization_endpoint"],
            self._client_id,
            "code",
            redirect_uri=self._redirect,
            scope="openid",
            state=state,
            code_challenge=create_s256_code_challenge(verifier),
            code_challenge_method="S256",
            nonce=nonce,
        )
        return url, state, verifier, nonce

    def exchange(self, code: str, verifier: str, nonce: str | None = None) -> dict:
        meta = self.metadata()
        tokens = self._post(
            meta["token_endpoint"],
            {
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": verifier,
                "redirect_uri": self._redirect,
            },
        )
        if self._keys is not None:
            self._check_id_token(tokens.get("id_token"), nonce)
        return tokens

    def _check_id_token(self, id_token: str | None, nonce: str | None) -> None:
        """The id token proves this sign-in is the one we started (nonce, audience, issuer)."""
        import jwt

        if not id_token or not nonce:
            raise AuthRefused("Keycloak gave no id token for this sign-in.")
        try:
            header = jwt.get_unverified_header(id_token)
            key = self._keys.get(str(header.get("kid", "")))
            if key is None or key.algorithm != header.get("alg"):
                raise AuthRefused("The id token is not signed by a known key.")
            claims = jwt.decode(
                id_token,
                key.key,
                algorithms=[key.algorithm],
                audience=self._client_id,
                issuer=self.issuer,
                leeway=60,
            )
        except jwt.PyJWTError as exc:
            raise AuthRefused("The id token was not accepted.") from exc
        if not secrets.compare_digest(str(claims.get("nonce", "")), nonce):
            raise AuthRefused("The id token belongs to a different sign-in.")

    def refresh(self, refresh_token: str) -> dict:
        meta = self.metadata()
        return self._post(
            meta["token_endpoint"], {"grant_type": "refresh_token", "refresh_token": refresh_token}
        )

    def identity(self, access_token: str) -> Verdict:
        verdict = self._verifier.verify(access_token)
        if not verdict.valid:
            raise AuthRefused("The access token was not accepted.")
        return verdict

    def logout(self, refresh_token: str | None) -> None:
        """End the Keycloak session; a failure is not the person's problem."""
        if not refresh_token:
            return
        try:
            meta = self.metadata()
            with httpx.Client(transport=self._transport, timeout=self._timeout) as http:
                http.post(
                    meta["end_session_endpoint"],
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._secret_value(),
                        "refresh_token": refresh_token,
                    },
                )
        except (AuthDown, httpx.HTTPError):
            return
