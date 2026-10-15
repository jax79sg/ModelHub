"""The Catalog's HTTP interface (contracts C2 and C3; rules BR1.8, BR1.11, BR1.14 to BR1.18)."""

import json

import pytest
from conftest import C1, C2, make_record
from fastapi.testclient import TestClient
from modelhub_catalog.app import create_app
from modelhub_testkit.issuer import FakeIssuer


@pytest.fixture
def issuer():
    return FakeIssuer()


@pytest.fixture
def client(store, issuer):
    return TestClient(
        create_app(store, jwks_fetch=issuer.jwks, issuer=issuer.issuer, audience=issuer.audience)
    )


def person(issuer, name="ada", admin=False, sub=None):
    return {"Authorization": f"Bearer {issuer.token(username=name, sub=sub or name, admin=admin)}"}


def service(issuer):
    return {"Authorization": f"Bearer {issuer.service_token()}"}


def put_version(client, issuer, model="acme/tiny", commit=C1, record=None, docs=None, headers=None):
    record = record or make_record(model, commit)
    docs = (
        docs
        if docs is not None
        else [
            ("readme/README.md", b"# Tiny quantized model", "text/markdown"),
            ("response/model.json", b'{"a": 1}', "application/json"),
        ]
    )
    files = [("documents", (name, data, ctype)) for name, data, ctype in docs]
    return client.put(
        f"/v1/models/{model}/versions/{commit}",
        data={"record": json.dumps(record)},
        files=files or None,
        headers=headers or service(issuer),
    )


# --- access ------------------------------------------------------------------------------------
def test_every_route_needs_a_token(client):
    for method, path in [
        ("GET", "/v1/models"),
        ("GET", "/v1/trail"),
        ("GET", "/v1/tokens"),
        ("POST", "/v1/tokens"),
        ("GET", "/v1/versions"),
    ]:
        assert client.request(method, path).status_code == 401, (method, path)


def test_health_is_open_and_ready_shows_the_database(client):
    assert client.get("/healthz").status_code == 200
    r = client.get("/readyz")
    assert r.status_code == 200 and r.json()["checks"] == {"database": "ok"}


def test_writes_need_the_import_services_identity(client, issuer):
    assert put_version(client, issuer, headers=person(issuer)).status_code == 403
    assert (
        client.post(
            f"/v1/models/acme/tiny/versions/{C1}/removal", json={}, headers=person(issuer)
        ).status_code
        == 403
    )
    assert client.get("/v1/versions", headers=person(issuer)).status_code == 403
    assert (
        client.post(
            "/v1/tokens/introspect", json={"token": "x"}, headers=person(issuer)
        ).status_code
        == 403
    )


# --- storing and reading ---------------------------------------------------------------------
def test_a_version_is_stored_201_repeated_200_and_a_different_record_409(client, issuer):
    assert put_version(client, issuer).status_code == 201
    assert put_version(client, issuer).status_code == 200
    changed = make_record(version={"likes": 99})
    r = put_version(client, issuer, record=changed)
    assert r.status_code == 409 and r.json()["code"] == "record_conflict"


def test_an_invalid_record_is_422_with_the_field(client, issuer):
    bad = make_record()
    del bad["importRecord"]["computer"]
    r = put_version(client, issuer, record=bad)
    assert r.status_code == 422 and r.json()["code"] == "invalid_record"
    assert "computer" in r.json()["message"]


def test_a_record_that_is_not_json_is_422(client, issuer):
    r = client.put(
        f"/v1/models/acme/tiny/versions/{C1}", data={"record": "{not json"}, headers=service(issuer)
    )
    assert r.status_code == 422


def test_a_document_with_a_bad_name_is_422(client, issuer):
    r = put_version(client, issuer, docs=[("readme/../x", b"x", "text/plain")])
    assert r.status_code == 422


def test_reads_work_for_any_signed_in_person(client, issuer):
    put_version(client, issuer)
    h = person(issuer, "bob")
    m = client.get("/v1/models/acme/tiny", headers=h)
    assert m.status_code == 200 and m.json()["versions"][0]["commit"] == C1
    v = client.get(f"/v1/models/acme/tiny/versions/{C1}", headers=h)
    assert v.status_code == 200 and v.json()["downloads"] == 1000
    assert client.get("/v1/models/nope/none", headers=h).json()["code"] == "not_found"
    assert client.get(f"/v1/models/acme/tiny/versions/{C2}", headers=h).status_code == 404


def test_the_list_filters_sorts_and_refuses_unknown_values(client, issuer):
    put_version(client, issuer)
    h = person(issuer)
    r = client.get("/v1/models", params={"task": "text-generation", "sort": "likes"}, headers=h)
    assert r.status_code == 200 and r.json()["total"] == 1
    bad = client.get("/v1/models", params={"sort": "bogus"}, headers=h)
    assert bad.status_code == 422 and bad.json()["code"] == "invalid_query"
    q = client.get("/v1/models", params={"q": "quantized"}, headers=h)
    assert q.json()["total"] == 1


# --- documents ---------------------------------------------------------------------------------
def test_a_document_is_served_as_data_with_safe_headers(client, issuer):
    put_version(
        client,
        issuer,
        docs=[
            ("readme/README.md", b"# Tiny", "text/markdown"),
            ("picture/p.svg", b"<svg onload=alert(1)>", "image/svg+xml"),
            ("response/page.html", b"<script>x</script>", "text/html"),
        ],
    )
    h = person(issuer)
    base = f"/v1/models/acme/tiny/versions/{C1}/documents"
    r = client.get(f"{base}/readme/README.md", headers=h)
    assert r.status_code == 200 and r.content == b"# Tiny"
    assert r.headers["content-type"].startswith("text/markdown")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in r.headers["content-security-policy"]
    assert r.headers["content-disposition"].startswith("attachment")
    for name in ("picture/p.svg", "response/page.html"):
        rr = client.get(f"{base}/{name}", headers=h)
        assert rr.headers["content-type"] == "application/octet-stream", name


def test_a_missing_document_is_404_and_a_removed_versions_document_is_410(client, issuer):
    put_version(client, issuer)
    h = person(issuer)
    base = f"/v1/models/acme/tiny/versions/{C1}"
    assert client.get(f"{base}/documents/readme/nope.md", headers=h).status_code == 404
    r = client.post(f"{base}/removal", json={"removedBy": "admin1"}, headers=service(issuer))
    assert r.status_code == 200
    assert client.get(f"{base}/documents/readme/README.md", headers=h).status_code == 410
    again = client.post(f"{base}/removal", json={"removedBy": "admin1"}, headers=service(issuer))
    assert again.status_code == 409


# --- retention list and trail -------------------------------------------------------------------
def test_the_versions_list_and_the_trail(client, issuer):
    put_version(client, issuer)
    r = client.get("/v1/versions", params={"state": "imported"}, headers=service(issuer))
    assert r.status_code == 200 and r.json()["items"][0]["commit"] == C1
    assert (
        client.get("/v1/versions", params={"state": "weird"}, headers=service(issuer)).status_code
        == 422
    )
    t = client.get(
        "/v1/trail", params={"model": "acme/tiny", "person": "u1"}, headers=person(issuer)
    )
    assert t.status_code == 200 and t.json()["items"][0]["outcome"] == "imported"


def test_an_import_only_record_is_201_and_needs_an_imported_version(client, issuer):
    rec = make_record(importRecord={"outcome": "skipped"})
    del rec["version"]
    r = client.put(
        f"/v1/models/acme/tiny/versions/{C1}",
        data={"record": json.dumps(rec)},
        headers=service(issuer),
    )
    assert r.status_code == 422
    put_version(client, issuer)
    r = client.put(
        f"/v1/models/acme/tiny/versions/{C1}",
        data={"record": json.dumps(rec)},
        headers=service(issuer),
    )
    assert r.status_code == 201


# --- personal tokens ---------------------------------------------------------------------------
def test_a_person_makes_a_token_once_sees_it_listed_without_the_value_and_revokes_it(
    client, issuer
):
    h = person(issuer, "ada")
    made = client.post("/v1/tokens", json={"name": "laptop"}, headers=h)
    assert made.status_code == 201
    body = made.json()
    assert body["token"].startswith("mhi_") and body["scope"] == "import" and body["expiresAt"]
    listing = client.get("/v1/tokens", headers=h)
    text = listing.text
    assert body["token"] not in text and "value_hash" not in text
    row = listing.json()["items"][0]
    assert row["prefix"] == body["token"][:8] and row["name"] == "laptop"
    assert client.delete(f"/v1/tokens/{body['tokenId']}", headers=h).status_code == 204
    assert client.delete(f"/v1/tokens/{body['tokenId']}", headers=h).status_code == 204
    assert client.get("/v1/tokens", headers=h).json()["items"][0]["revoked_at"]


def test_a_service_identity_cannot_make_a_personal_token(client, issuer):
    assert client.post("/v1/tokens", json={"name": "x"}, headers=service(issuer)).status_code == 403


def test_a_bad_token_name_is_422(client, issuer):
    for name in ["", " ", "x" * 61]:
        r = client.post("/v1/tokens", json={"name": name}, headers=person(issuer))
        assert r.status_code == 422, name


def test_other_peoples_tokens_are_not_visible_or_revocable_but_an_administrator_can(client, issuer):
    made = client.post("/v1/tokens", json={"name": "t"}, headers=person(issuer, "ada")).json()
    bob = person(issuer, "bob")
    assert client.get("/v1/tokens", headers=bob).json()["items"] == []
    assert client.delete(f"/v1/tokens/{made['tokenId']}", headers=bob).status_code == 404
    admin = person(issuer, "root", admin=True)
    assert len(client.get("/v1/tokens", params={"all": "true"}, headers=admin).json()["items"]) == 1
    assert client.get("/v1/tokens", params={"all": "true"}, headers=bob).json()["items"] == []
    assert client.delete(f"/v1/tokens/{made['tokenId']}", headers=admin).status_code == 204


def test_introspection_by_the_service(client, issuer):
    made = client.post("/v1/tokens", json={"name": "t"}, headers=person(issuer, "ada")).json()
    svc = service(issuer)
    ok = client.post("/v1/tokens/introspect", json={"token": made["token"]}, headers=svc).json()
    assert ok["active"] is True and ok["ownerName"] == "ada" and ok["scope"] == "import"
    client.delete(f"/v1/tokens/{made['tokenId']}", headers=person(issuer, "ada"))
    gone = client.post("/v1/tokens/introspect", json={"token": made["token"]}, headers=svc).json()
    assert gone == {"active": False, "reason": "revoked"}
    unknown = client.post("/v1/tokens/introspect", json={"token": "mhi_nope"}, headers=svc).json()
    assert unknown == {"active": False, "reason": "unknown"}


def test_the_token_value_never_reaches_the_logs(client, issuer, caplog):
    import io
    import logging

    from modelhub_common.logs import JsonFormatter

    stream = io.StringIO()
    logger = logging.getLogger("modelhub")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter("catalog"))
    logger.addHandler(handler)
    logger.setLevel("INFO")
    try:
        made = client.post("/v1/tokens", json={"name": "t"}, headers=person(issuer)).json()
        client.post("/v1/tokens/introspect", json={"token": made["token"]}, headers=service(issuer))
    finally:
        logger.removeHandler(handler)
    assert made["token"] not in stream.getvalue()


def test_the_token_lifetime_is_an_administrator_setting_from_1_to_365_days(client, issuer):
    admin, bob = person(issuer, "root", admin=True), person(issuer, "bob")
    assert client.get("/v1/settings/token-lifetime", headers=bob).json() == {"days": 90}
    assert (
        client.put("/v1/settings/token-lifetime", json={"days": 30}, headers=bob).status_code == 403
    )
    assert client.put("/v1/settings/token-lifetime", json={"days": 30}, headers=admin).json() == {
        "days": 30
    }
    for days in (0, 366, "x", True):
        r = client.put("/v1/settings/token-lifetime", json={"days": days}, headers=admin)
        assert r.status_code == 422, days
