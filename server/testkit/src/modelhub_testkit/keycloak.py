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
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from modelhub_testkit.issuer import FakeIssuer


class FakeKeycloak:
    def __init__(self, issuer: FakeIssuer | None = None, client_id: str = "modelhub") -> None:
        self.issuer = issuer or FakeIssuer()
        self.client_id = client_id
        self.base = self.issuer.issuer
        self.down = False  # every call fails as if Keycloak could not be reached
        self.refuse_refresh = False
        self.wrong_nonce = False  # give an id token for some other sign-in
        self.no_id_token = False
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
            "nonce": q.get("nonce"),
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

    def _issue(self, user: dict, nonce: str | None = None) -> dict:
        refresh = uuid.uuid4().hex
        self._refresh[refresh] = user
        answer = {
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
        if nonce is not None and not self.no_id_token:
            answer["id_token"] = self.issuer.token(
                sub=user["sub"],
                username=user["username"],
                audience=self.client_id,
                expires_in=self.access_lifetime,
                extra={"nonce": "other" if self.wrong_nonce else nonce},
            )
        return answer

    def _token(self, form: dict) -> httpx.Response:
        grant = form["grant_type"][0]
        if grant == "authorization_code":
            code = self._codes.pop(form["code"][0], None)
            verifier = form.get("code_verifier", [""])[0]
            digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            if code is None or digest.rstrip(b"=").decode() != code["challenge"]:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(200, json=self._issue(code["user"], code.get("nonce")))
        if grant == "client_credentials":
            return httpx.Response(
                200,
                json={
                    "access_token": self.issuer.service_token(expires_in=self.access_lifetime),
                    "expires_in": self.access_lifetime,
                    "token_type": "Bearer",
                },
            )
        if grant == "refresh_token":
            user = self._refresh.pop(form["refresh_token"][0], None)
            if user is None or self.refuse_refresh:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(200, json=self._issue(user))
        return httpx.Response(400, content=json.dumps({"error": "unsupported_grant_type"}))


class KeycloakServer:
    """The same fake sign-in on a real local port, for whole-stack checks.

    The browser's visit to the sign-in page is automatic: ``/auth`` signs in the person named by
    ``login_hint`` (default ada; ``admin=1`` gives the administrator role) and sends the browser
    straight back with a code. Never shipped; it binds the local machine only.
    """

    def __init__(
        self,
        client_id: str = "modelhub",
        host: str = "127.0.0.1",
        public_host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        import socket

        self.host = host
        if not port:
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
        self.port = port
        self.url = f"http://{public_host}:{self.port}"
        self.realm = f"{self.url}/realms/modelhub"
        self.keycloak = FakeKeycloak(FakeIssuer(issuer=self.realm), client_id=client_id)
        self._server = None
        self._thread = None

    @property
    def issuer(self) -> FakeIssuer:
        return self.keycloak.issuer

    def _app(self):
        app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
        kc = self.keycloak
        oidc = "/realms/modelhub/protocol/openid-connect"

        @app.get("/realms/modelhub/.well-known/openid-configuration")
        def discovery():
            base = self.realm + "/protocol/openid-connect"
            return {
                "issuer": self.realm,
                "authorization_endpoint": base + "/auth",
                "token_endpoint": base + "/token",
                "end_session_endpoint": base + "/logout",
                "jwks_uri": base + "/certs",
            }

        @app.get(oidc + "/certs")
        def certs():
            return kc.issuer.jwks()

        @app.get(oidc + "/auth")
        def auth(request: Request, login_hint: str = "ada", admin: int = 0):
            back = kc.authorize(str(request.url), username=login_hint, admin=bool(admin))
            return RedirectResponse(back, 302)

        @app.post(oidc + "/token")
        async def token(request: Request):
            from urllib.parse import parse_qs

            form = parse_qs((await request.body()).decode(), keep_blank_values=True)
            answer = kc._token(form)
            return JSONResponse(answer.json(), status_code=answer.status_code)

        @app.post(oidc + "/logout")
        def logout():
            return Response(status_code=204)

        return app

    def start(self) -> KeycloakServer:
        import threading
        import time

        import uvicorn

        config = uvicorn.Config(
            self._app(), host=self.host, port=self.port, log_level="warning", lifespan="off"
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        deadline = time.monotonic() + 20
        while not self._server.started:
            if time.monotonic() > deadline:
                raise RuntimeError("the sign-in stand-in did not start")
            time.sleep(0.01)
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=10)

    def __enter__(self) -> KeycloakServer:  # noqa: PYI034 - Self needs Python 3.11
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()
