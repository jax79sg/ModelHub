"""Start the service: settings and secrets, upgrade steps, restart sweep, then the app (BR1.21)."""

from __future__ import annotations

import os
import sys
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import FastAPI
from modelhub_common.config import SHARED_SETTINGS, Setting, StartupError, load_config
from modelhub_common.keys import http_fetcher
from modelhub_common.logs import configure_logging
from modelhub_common.secrets import Secret

from modelhub_artifactory_service.app import create_app
from modelhub_artifactory_service.catalog_client import CatalogClient, ServiceTokenProvider
from modelhub_artifactory_service.db import make_pool, migrate
from modelhub_artifactory_service.gateway import Gateway, JfUploader
from modelhub_artifactory_service.importer import Importer
from modelhub_artifactory_service.keys import TrustedKeys
from modelhub_artifactory_service.retention import Retention

SECRETS = ["database_password", "artifactory_token", "service_client_secret"]
SETTINGS = [
    *SHARED_SETTINGS,
    Setting("MODELHUB_DATABASE_HOST", str, required=True),
    Setting("MODELHUB_DATABASE_PORT", int, default=5432, minimum=1),
    Setting("MODELHUB_DATABASE_NAME", str, required=True),
    Setting("MODELHUB_DATABASE_USER", str, required=True),
    Setting("MODELHUB_DB_POOL_SIZE", int, default=10, minimum=1),
    Setting("MODELHUB_PORT", int, default=8000, minimum=1),
    Setting("MODELHUB_ARTIFACTORY_URL", str, required=True),
    Setting("MODELHUB_ARTIFACTORY_REPO", str, required=True),
    Setting("MODELHUB_UPLOAD_TOOL", str, default="huggingface_hub"),
    Setting("MODELHUB_CATALOG_URL", str, required=True),
    Setting("MODELHUB_SERVICE_TOKEN_URL", str, default=""),
    Setting("MODELHUB_SERVICE_CLIENT_ID", str, default="modelhub-artifactory-service"),
    Setting("MODELHUB_WORK_DIR", str, default="/import-work"),
    Setting("MODELHUB_MIN_CLIENT_VERSION", str, default="0.0.0"),
]
IDLE_SWEEP_SECONDS = 600


def database_url(cfg: Mapping, password: Secret) -> str:
    return (
        f"postgresql://{quote(cfg['MODELHUB_DATABASE_USER'], safe='')}:"
        f"{quote(password.reveal(), safe='')}@{cfg['MODELHUB_DATABASE_HOST']}:"
        f"{cfg['MODELHUB_DATABASE_PORT']}/{cfg['MODELHUB_DATABASE_NAME']}"
    )


def build_app(
    environ: Mapping[str, str] | None = None,
    jwks_fetch: Callable[[], dict] | None = None,
    catalog_http: httpx.Client | None = None,
    token_http: httpx.Client | None = None,
) -> FastAPI:
    env = environ if environ is not None else os.environ
    cfg, secrets = load_config(SETTINGS, SECRETS, environ=env)
    url = database_url(cfg, secrets["database_password"])
    migrate(url)
    pool = make_pool(url, cfg["MODELHUB_DB_POOL_SIZE"])
    issuer = cfg["MODELHUB_REALM_ISSUER"]
    timeouts = httpx.Timeout(cfg["MODELHUB_READ_TIMEOUT"], connect=cfg["MODELHUB_CONNECT_TIMEOUT"])
    token_url = (
        cfg["MODELHUB_SERVICE_TOKEN_URL"] or issuer.rstrip("/") + "/protocol/openid-connect/token"
    )
    provider = ServiceTokenProvider(
        token_url,
        cfg["MODELHUB_SERVICE_CLIENT_ID"],
        lambda: secrets["service_client_secret"].reveal(),
        http=token_http or httpx.Client(timeout=timeouts),
    )
    catalog = CatalogClient(
        catalog_http or httpx.Client(timeout=timeouts), cfg["MODELHUB_CATALOG_URL"], provider
    )
    token = secrets["artifactory_token"].reveal()
    uploader = (
        JfUploader(cfg["MODELHUB_ARTIFACTORY_URL"], cfg["MODELHUB_ARTIFACTORY_REPO"], token)
        if cfg["MODELHUB_UPLOAD_TOOL"] == "jf"
        else None
    )
    gateway = Gateway(
        cfg["MODELHUB_ARTIFACTORY_URL"],
        cfg["MODELHUB_ARTIFACTORY_REPO"],
        token,
        uploader=uploader,
        connect_timeout=cfg["MODELHUB_CONNECT_TIMEOUT"],
        read_timeout=cfg["MODELHUB_READ_TIMEOUT"],
    )
    keys = TrustedKeys(pool)
    importer = Importer(pool, keys, gateway, catalog, Path(cfg["MODELHUB_WORK_DIR"]))
    importer.sweep_restart()
    fetch = jwks_fetch or http_fetcher(
        cfg["MODELHUB_JWKS_URL"] or issuer.rstrip("/") + "/protocol/openid-connect/certs",
        connect=cfg["MODELHUB_CONNECT_TIMEOUT"],
        read=cfg["MODELHUB_READ_TIMEOUT"],
    )
    app = create_app(
        importer,
        Retention(pool, gateway, catalog),
        keys,
        catalog,
        jwks_fetch=fetch,
        issuer=issuer,
        audience=cfg["MODELHUB_AUDIENCE"],
        min_client_version=cfg["MODELHUB_MIN_CLIENT_VERSION"],
    )
    app.state.settings = cfg
    return app


def _sweep_forever(importer: Importer, stop: threading.Event) -> None:
    while not stop.wait(IDLE_SWEEP_SECONDS):
        try:
            importer.sweep_idle()
        except Exception:
            import logging

            logging.getLogger("modelhub.import").exception("idle sweep failed")


def main() -> int:
    import uvicorn

    try:
        _, secrets = load_config(SETTINGS, SECRETS)
    except StartupError as exc:
        sys.stderr.write(str(exc) + "\n")  # names only, never values
        return 1
    configure_logging(
        "artifactory-service", os.environ.get("MODELHUB_LOG_LEVEL", "info"), secrets.values()
    )
    try:
        app = build_app()
    except StartupError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1
    stop = threading.Event()
    threading.Thread(
        target=_sweep_forever, args=(app.state.importer, stop), daemon=True, name="idle-sweep"
    ).start()
    uvicorn.run(app, host="0.0.0.0", port=app.state.settings["MODELHUB_PORT"], log_config=None)
    stop.set()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
