import json
from datetime import datetime, timedelta, timezone

import pytest
from modelhub_artifactory_service import db
from modelhub_artifactory_service.catalog_client import CatalogClient
from modelhub_artifactory_service.gateway import Gateway
from modelhub_artifactory_service.importer import Importer
from modelhub_artifactory_service.keys import TrustedKeys
from modelhub_stand_in.server import StandIn
from modelhub_testkit.bundles import make_bundle


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, **kw):
        self.now += timedelta(**kw)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def pool(fresh_database):
    db.migrate(fresh_database)
    p = db.make_pool(fresh_database)
    yield p
    p.close()


@pytest.fixture
def issuer():
    from modelhub_testkit.issuer import FakeIssuer

    return FakeIssuer()


@pytest.fixture
def catalog(fresh_database, issuer):
    """The real Catalog app, on the same database (it uses the public schema; this service has
    its own), reached as an HTTP client would reach it."""
    from fastapi.testclient import TestClient
    from modelhub_catalog import db as catalog_db
    from modelhub_catalog.app import create_app
    from modelhub_catalog.store import CatalogStore

    catalog_db.migrate(fresh_database)
    store = CatalogStore(fresh_database, pepper=b"pepper-" + b"p" * 24)
    client = TestClient(
        create_app(store, jwks_fetch=issuer.jwks, issuer=issuer.issuer, audience=issuer.audience)
    )
    client.store = store
    yield client
    store.close()


@pytest.fixture(autouse=True)
def _no_xet(monkeypatch):
    monkeypatch.setenv("HF_HUB_DISABLE_XET", "1")
    monkeypatch.setenv("HF_HUB_DISABLE_TELEMETRY", "1")


@pytest.fixture
def stand_in(tmp_path):
    with StandIn(token="svc-token-1", workdir=tmp_path / "si") as s:
        yield s


@pytest.fixture
def bundle(tmp_path):
    return make_bundle(tmp_path / "b")


@pytest.fixture
def world(pool, clock, catalog, issuer, stand_in, bundle, tmp_path):
    keys = TrustedKeys(pool, clock)
    trust(keys, bundle)
    gateway = Gateway(stand_in.url, stand_in.repo_key, stand_in.token)
    client = CatalogClient(catalog, "", lambda: issuer.service_token())
    work = tmp_path / "work"
    imp = Importer(
        pool, keys, gateway, client, work, clock=clock, sleep=lambda s: None, jitter=lambda: 0
    )
    imp.sleeps = []
    return imp


def trust(keys, made, label="key"):
    doc = made.public_key
    keys.add(json.dumps(doc), doc["fingerprint"], label, "u0", "root")
