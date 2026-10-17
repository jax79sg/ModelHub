"""Start the portal: settings, the sign-in client secret from a file, then the app (NFR5.11)."""

from __future__ import annotations

import contextlib
import os
import sys
from collections.abc import Callable, Mapping

import httpx
from fastapi import FastAPI
from modelhub_common.config import SHARED_SETTINGS, Setting, StartupError, load_config
from modelhub_common.keys import KeySet, http_fetcher
from modelhub_common.logs import configure_logging
from modelhub_common.tokens import TokenVerifier

from modelhub_portal.app import Settings, create_app
from modelhub_portal.catalog_client import Catalog
from modelhub_portal.oidc import Oidc
from modelhub_portal.service_client import RetentionService

SECRETS = ["keycloak_client_secret"]
SETTINGS = [
    *SHARED_SETTINGS,
    Setting("MODELHUB_PORT", int, default=8000, minimum=1),
    Setting("MODELHUB_PUBLIC_URL", str, required=True),
    Setting("MODELHUB_CATALOG_URL", str, required=True),
    Setting("MODELHUB_SERVICE_URL", str, required=True),
    Setting("MODELHUB_KEYCLOAK_CLIENT_ID", str, default="modelhub"),
    Setting("MODELHUB_ARTIFACTORY_URL", str, required=True),
    Setting("MODELHUB_HF_REPO_KEY", str, required=True),
    Setting("MODELHUB_SESSION_IDLE_HOURS", float, default=8, minimum=0, exclusive=True),
]


def build_app(
    environ: Mapping[str, str] | None = None,
    jwks_fetch: Callable[[], dict] | None = None,
    catalog_http: httpx.Client | None = None,
    oidc_transport: httpx.BaseTransport | None = None,
) -> FastAPI:
    env = environ if environ is not None else os.environ
    cfg, secrets = load_config(SETTINGS, SECRETS, environ=env)
    issuer = cfg["MODELHUB_REALM_ISSUER"]
    fetch = jwks_fetch or http_fetcher(
        cfg["MODELHUB_JWKS_URL"] or issuer.rstrip("/") + "/protocol/openid-connect/certs",
        connect=cfg["MODELHUB_CONNECT_TIMEOUT"],
        read=cfg["MODELHUB_READ_TIMEOUT"],
    )
    keys = KeySet(fetch)
    with contextlib.suppress(Exception):  # start anyway; the keys are fetched again when needed
        keys.load()
    verifier = TokenVerifier(keys, issuer=issuer, audience=cfg["MODELHUB_AUDIENCE"])
    public = cfg["MODELHUB_PUBLIC_URL"].rstrip("/")
    timeouts = httpx.Timeout(cfg["MODELHUB_READ_TIMEOUT"], connect=cfg["MODELHUB_CONNECT_TIMEOUT"])
    oidc = Oidc(
        issuer,
        cfg["MODELHUB_KEYCLOAK_CLIENT_ID"],
        lambda: secrets["keycloak_client_secret"].reveal(),
        public + "/auth/callback",
        verifier,
        keys=keys,
        transport=oidc_transport,
        timeout=timeouts,
    )
    http = catalog_http or httpx.Client(timeout=timeouts)
    catalog = Catalog(http, cfg["MODELHUB_CATALOG_URL"])
    settings = Settings(
        base_url=public,
        artifactory_url=cfg["MODELHUB_ARTIFACTORY_URL"],
        hf_repo_key=cfg["MODELHUB_HF_REPO_KEY"],
        session_idle_hours=cfg["MODELHUB_SESSION_IDLE_HOURS"],
    )
    service = RetentionService(http, cfg["MODELHUB_SERVICE_URL"])
    app = create_app(settings, oidc, catalog, service=service)
    app.state.settings = cfg
    return app


def main() -> int:
    import uvicorn

    try:
        _, secrets = load_config(SETTINGS, SECRETS)
    except StartupError as exc:
        sys.stderr.write(str(exc) + "\n")  # names only, never values
        return 1
    configure_logging("portal", os.environ.get("MODELHUB_LOG_LEVEL", "info"), secrets.values())
    try:
        app = build_app()
    except StartupError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1
    # One process: sessions live in memory (NFR9.4).
    uvicorn.run(app, host="0.0.0.0", port=app.state.settings["MODELHUB_PORT"], log_config=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
