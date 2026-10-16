import httpx
import pytest
from fastapi.testclient import TestClient
from modelhub_common.keys import KeySet
from modelhub_common.tokens import TokenVerifier
from modelhub_portal.app import Settings, create_app
from modelhub_portal.catalog_client import Catalog
from modelhub_portal.oidc import Oidc
from modelhub_testkit.keycloak import FakeKeycloak

BASE = "https://portal.test"


class Clock:
    def __init__(self):
        self.now = 1_800_000_000.0

    def __call__(self):
        return self.now

    def advance(self, seconds=0, hours=0):
        self.now += seconds + hours * 3600


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def keycloak():
    return FakeKeycloak()


@pytest.fixture
def catalog_http(fresh_database, keycloak):
    """The real Catalog app on a real database, reached the way the portal reaches it."""
    from modelhub_catalog import db as catalog_db
    from modelhub_catalog.app import create_app as create_catalog
    from modelhub_catalog.store import CatalogStore

    catalog_db.migrate(fresh_database)
    issuer = keycloak.issuer
    store = CatalogStore(fresh_database, pepper=b"pepper-" + b"p" * 24)
    client = TestClient(
        create_catalog(
            store, jwks_fetch=issuer.jwks, issuer=issuer.issuer, audience=issuer.audience
        )
    )
    client.store = store
    yield client
    store.close()


def make_portal(keycloak, catalog_http, clock, **settings):
    issuer = keycloak.issuer
    keys = KeySet(issuer.jwks)
    keys.load()
    verifier = TokenVerifier(keys, issuer=issuer.issuer, audience=issuer.audience)
    oidc = Oidc(
        issuer.issuer,
        keycloak.client_id,
        lambda: "client-secret-for-tests",
        BASE + "/auth/callback",
        verifier,
        transport=keycloak.transport(),
    )
    cfg = Settings(
        base_url=BASE,
        artifactory_url="https://artifactory.test",
        hf_repo_key="hf-local",
        **settings,
    )
    app = create_app(cfg, oidc, Catalog(catalog_http), clock=clock)
    return TestClient(app, base_url=BASE, follow_redirects=False)


@pytest.fixture
def portal(keycloak, catalog_http, clock):
    return make_portal(keycloak, catalog_http, clock)


def sign_in(portal, keycloak, username="ada", admin=False):
    """Walk the browser through the sign-in and return the page it lands on."""
    r = portal.get("/auth/login")
    assert r.status_code == 302, r.text
    back = keycloak.authorize(r.headers["location"], username=username, admin=admin)
    return portal.get(back.removeprefix(BASE))


@pytest.fixture
def signed_in(portal, keycloak):
    sign_in(portal, keycloak)
    return portal


def csrf_of(portal) -> str:
    html = portal.get("/account/tokens").text
    marker = 'name="_csrf" value="'
    start = html.index(marker) + len(marker)
    return html[start : html.index('"', start)]


_ = httpx
