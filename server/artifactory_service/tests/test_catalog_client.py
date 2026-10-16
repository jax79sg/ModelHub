"""The service's client of the Catalog and the service token (contracts C2, C3, C6; ADR-002)."""

import uuid

import httpx
import pytest
from modelhub_artifactory_service.catalog_client import (
    AuthUnavailable,
    CatalogClient,
    CatalogConflict,
    CatalogInvalid,
    CatalogUnavailable,
    ServiceTokenProvider,
)

SECRET = "s" + uuid.uuid4().hex
LEAK = "l" + uuid.uuid4().hex
C1 = "1" * 40
MODEL = "acme/tiny"


def record(commit=C1, **over):
    version = {
        "model_id": MODEL,
        "commit": commit,
        "captured_at": "2026-01-02T03:04:05Z",
        "license": "mit",
        "tags": ["a"],
        "task": "text-generation",
        "downloads": 5,
        "files": [{"path": "config.json", "size_bytes": 3, "sha256": "a" * 64, "downloaded": True}],
    }
    imp = {
        "importedBy": {"id": "u1", "name": "ada"},
        "importedAt": "2026-02-01T00:00:00Z",
        "computer": "pc",
        "bundleName": "b",
        "bundleSha256": "c" * 64,
        "signingKeyFingerprint": "aaaa-bbbb",
        "toolVersion": "1",
        "checkResults": {"ok": True},
        "outcome": "imported",
    }
    imp.update(over)
    return {"version": version, "importRecord": imp}


DOCS = [("readme/README.md", b"# Tiny", "text/markdown")]


@pytest.fixture
def client(catalog, issuer):
    provider = lambda: issuer.service_token()
    return CatalogClient(catalog, "", provider)


def test_put_get_and_repeat(client):
    assert client.put_version(MODEL, C1, record(), DOCS) == "created"
    assert client.put_version(MODEL, C1, record(), DOCS) == "unchanged"
    v = client.get_version(MODEL, C1)
    assert v["state"] == "imported" and v["downloads"] == 5
    assert client.get_version(MODEL, "2" * 40) is None


def test_a_different_record_is_a_conflict(client):
    client.put_version(MODEL, C1, record(), DOCS)
    changed = record()
    changed["version"]["downloads"] = 6
    with pytest.raises(CatalogConflict):
        client.put_version(MODEL, C1, changed, DOCS)


def test_an_invalid_record_names_the_field(client):
    bad = record()
    del bad["importRecord"]["computer"]
    with pytest.raises(CatalogInvalid) as err:
        client.put_version(MODEL, C1, bad, DOCS)
    assert "computer" in str(err.value)


def test_an_import_only_record_and_removal(client):
    client.put_version(MODEL, C1, record(), DOCS)
    only = record(outcome="skipped")
    del only["version"]
    assert client.put_import_only(MODEL, C1, only) == "recorded"
    assert client.mark_removed(MODEL, C1, "root") == "ok"
    assert client.mark_removed(MODEL, C1, "root") == "conflict"


def test_introspecting_a_personal_token(client, catalog, issuer):
    made = catalog.post(
        "/v1/tokens",
        json={"name": "t"},
        headers={"Authorization": f"Bearer {issuer.token(username='ada', sub='u1')}"},
    ).json()
    assert client.introspect(made["token"])["ownerName"] == "ada"
    assert client.introspect("mhi_nope") == {"active": False, "reason": "unknown"}


def test_the_catalog_being_down_is_a_retryable_error():
    def boom(request):
        raise httpx.ConnectError("down")

    c = CatalogClient(
        httpx.Client(transport=httpx.MockTransport(boom)), "http://catalog", lambda: "t"
    )
    with pytest.raises(CatalogUnavailable):
        c.get_version(MODEL, C1)


def test_a_server_error_is_retryable_and_a_bad_service_token_is_not_swallowed():
    c = CatalogClient(
        httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503))),
        "http://catalog",
        lambda: "t",
    )
    with pytest.raises(CatalogUnavailable):
        c.put_version(MODEL, C1, record(), DOCS)
    forbidden = CatalogClient(
        httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(403, json={"code": "forbidden"}))
        ),
        "http://catalog",
        lambda: "t",
    )
    with pytest.raises(AuthUnavailable):
        forbidden.get_version(MODEL, C1)


# --- the service token --------------------------------------------------------------------------
def test_the_service_token_is_got_by_client_credentials_and_cached_until_near_expiry(clock):
    calls = []

    def handler(request):
        calls.append(dict(httpx.QueryParams(request.content.decode())))
        return httpx.Response(200, json={"access_token": f"tok-{len(calls)}", "expires_in": 300})

    provider = ServiceTokenProvider(
        "http://kc/token",
        "modelhub-artifactory-service",
        lambda: SECRET,
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        clock=clock,
    )
    assert provider() == "tok-1" and provider() == "tok-1"
    assert calls[0]["grant_type"] == "client_credentials"
    assert calls[0]["client_id"] == "modelhub-artifactory-service"
    clock.advance(seconds=280)  # inside the 30 s margin before expiry
    assert provider() == "tok-2"


def test_a_token_endpoint_failure_is_auth_unavailable_and_never_shows_the_secret(clock):
    provider = ServiceTokenProvider(
        "http://kc/token",
        "c",
        lambda: LEAK,
        http=httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(401, text="bad " + LEAK))
        ),
        clock=clock,
    )
    with pytest.raises(AuthUnavailable) as err:
        provider()
    assert LEAK not in str(err.value)
