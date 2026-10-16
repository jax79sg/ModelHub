"""A fake Keycloak sign-in for tests: discovery, code flow with proof key, refresh and logout.

``transport()`` is an httpx transport the portal's client can use in place of the network. The
browser's visit to Keycloak is done by ``authorize(url, ...)``, which returns the address the
browser would be sent back to, with the code and state.
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx

from modelhub_testkit.issuer import FakeIssuer


class FakeKeycloak:
    def __init__(self, issuer: FakeIssuer | None = None, client_id: str = "modelhub") -> None:
        self.issuer = issuer or FakeIssuer()
        self.client_id = client_id
        self.base = self.issuer.issuer
        self.down = False  # every call fails as if Keycloak could not be reached
        self.refuse_refresh = False
        self.access_lifetime = 300
        self.calls: list[tuple[str, str]] = []
        self._codes: dict[str, dict] = {}
        self._refresh: dict[str, dict] = {}
        self.logged_out: list[str] = []

    # -- the browser's side ---------------------------------------------------------------------
    def authorize(
        self, url: str, username: str = "ada", sub: str | None = None, admin: bool = False
    ) -> str:
        parts = urlsplit(url)
        q = {k: v[0] for k, v in parse_qs(parts.query).items()}
        assert parts.path.endswith("/protocol/openid-connect/auth"), url
        assert q["response_type"] == "code" and q["code_challenge_method"] == "S256", q
        assert q["client_id"] == self.client_id
        code = uuid.uuid4().hex
        self._codes[code] = {
            "challenge": q["code_challenge"],
            "redirect_uri": q["redirect_uri"],
            "user": {"username": username, "sub": sub or "sub-" + username, "admin": admin},
        }
        return q["redirect_uri"] + "?" + urlencode({"code": code, "state": q["state"]})

    # -- the server's side ----------------------------------------------------------------------
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("keycloak is down")
        path = request.url.path
        self.calls.append((request.method, path))
        if path.endswith("/.well-known/openid-configuration"):
            oidc = self.base + "/protocol/openid-connect"
            return httpx.Response(
                200,
                json={
                    "issuer": self.base,
                    "authorization_endpoint": oidc + "/auth",
                    "token_endpoint": oidc + "/token",
                    "end_session_endpoint": oidc + "/logout",
                    "jwks_uri": oidc + "/certs",
                },
            )
        if path.endswith("/certs"):
            return httpx.Response(200, json=self.issuer.jwks())
        if path.endswith("/token"):
            return self._token(dict(parse_qs(request.content.decode(), keep_blank_values=True)))
        if path.endswith("/logout"):
            body = parse_qs(request.content.decode()) if request.content else {}
            self.logged_out.append((body.get("refresh_token") or [""])[0])
            return httpx.Response(204)
        return httpx.Response(404)

    def _issue(self, user: dict) -> dict:
        refresh = uuid.uuid4().hex
        self._refresh[refresh] = user
        return {
            "access_token": self.issuer.token(
                sub=user["sub"],
                username=user["username"],
                admin=user["admin"],
                expires_in=self.access_lifetime,
            ),
            "refresh_token": refresh,
            "expires_in": self.access_lifetime,
            "token_type": "Bearer",
        }

    def _token(self, form: dict) -> httpx.Response:
        grant = form["grant_type"][0]
        if grant == "authorization_code":
            code = self._codes.pop(form["code"][0], None)
            verifier = form.get("code_verifier", [""])[0]
            digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            if code is None or digest.rstrip(b"=").decode() != code["challenge"]:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(200, json=self._issue(code["user"]))
        if grant == "refresh_token":
            user = self._refresh.pop(form["refresh_token"][0], None)
            if user is None or self.refuse_refresh:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(200, json=self._issue(user))
        return httpx.Response(400, content=json.dumps({"error": "unsupported_grant_type"}))
