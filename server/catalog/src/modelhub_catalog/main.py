"""Start the Catalog: read settings and secrets, apply upgrade steps, build the app (BR1.6, BR1.7, BR1.21)."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from urllib.parse import quote

from fastapi import FastAPI
from modelhub_common.config import (
    SHARED_SETTINGS,
    Setting,
    StartupError,
    load_config,
    load_secrets,
)
from modelhub_common.keys import http_fetcher
from modelhub_common.logs import configure_logging
from modelhub_common.secrets import Secret

from .app import create_app
from .db import apply_grants, migrate
from .store import CatalogStore

SECRETS = ["database_password", "token_hash_pepper"]
SETTINGS = [
    *SHARED_SETTINGS,
    Setting("MODELHUB_DATABASE_HOST", str, required=True),
    Setting("MODELHUB_DATABASE_PORT", int, default=5432, minimum=1),
    Setting("MODELHUB_DATABASE_NAME", str, required=True),
    Setting("MODELHUB_DATABASE_USER", str, required=True),
    Setting("MODELHUB_MIGRATION_USER", str, default=""),
    Setting("MODELHUB_DB_POOL_SIZE", int, default=10, minimum=1),
    Setting("MODELHUB_PORT", int, default=8000, minimum=1),
]


def database_url(cfg: Mapping, password: Secret, user: str | None = None) -> str:
    return (
        f"postgresql://{quote(user or cfg['MODELHUB_DATABASE_USER'], safe='')}:"
        f"{quote(password.reveal(), safe='')}@{cfg['MODELHUB_DATABASE_HOST']}:"
        f"{cfg['MODELHUB_DATABASE_PORT']}/{cfg['MODELHUB_DATABASE_NAME']}"
    )


def build_app(
    environ: Mapping[str, str] | None = None,
    jwks_fetch: Callable[[], dict] | None = None,
) -> FastAPI:
    env = environ if environ is not None else os.environ
    cfg, secrets = load_config(SETTINGS, SECRETS, environ=env)
    url = database_url(cfg, secrets["database_password"])
    if cfg["MODELHUB_MIGRATION_USER"]:
        # The upgrade steps and the running role's rights are made by a separate migration role;
        # the service itself then runs as a role that cannot create or change objects (NFR5.5).
        extra = load_secrets(["database_migration_password"], environ=env)
        migration_url = database_url(
            cfg, extra["database_migration_password"], cfg["MODELHUB_MIGRATION_USER"]
        )
        migrate(migration_url)
        apply_grants(
            migration_url, cfg["MODELHUB_DATABASE_USER"], secrets["database_password"].reveal()
        )
    else:
        migrate(url)
    store = CatalogStore(
        url,
        pepper=secrets["token_hash_pepper"].reveal().encode(),
        pool_size=cfg["MODELHUB_DB_POOL_SIZE"],
    )
    issuer = cfg["MODELHUB_REALM_ISSUER"]
    fetch = jwks_fetch or http_fetcher(
        cfg["MODELHUB_JWKS_URL"] or issuer.rstrip("/") + "/protocol/openid-connect/certs",
        connect=cfg["MODELHUB_CONNECT_TIMEOUT"],
        read=cfg["MODELHUB_READ_TIMEOUT"],
    )
    app = create_app(store, jwks_fetch=fetch, issuer=issuer, audience=cfg["MODELHUB_AUDIENCE"])
    app.state.settings = cfg
    return app


def main() -> int:
    import uvicorn

    try:
        _, secrets = load_config(SETTINGS, SECRETS)
    except StartupError as exc:
        sys.stderr.write(str(exc) + "\n")  # names only, never values
        return 1
    configure_logging("catalog", os.environ.get("MODELHUB_LOG_LEVEL", "info"), secrets.values())
    try:
        app = build_app()
    except StartupError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 1
    uvicorn.run(app, host="0.0.0.0", port=app.state.settings["MODELHUB_PORT"], log_config=None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
