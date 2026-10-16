"""The service's HTTP interface: the import API (C1) and retention and keys (C4)."""

import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from modelhub_artifactory_service.app import create_app
from modelhub_artifactory_service.gateway import UploadNetworkError
from modelhub_artifactory_service.retention import Retention
from test_catalog_client import DOCS, record


@pytest.fixture
def api(world, catalog, issuer):
    retention = Retention(world.pool, world.gateway, world.catalog, world.clock)
    app = create_app(
        world,
        retention,
        world.keys,
        world.catalog,
        jwks_fetch=issuer.jwks,
        issuer=issuer.issuer,
        audience=issuer.audience,
        min_client_version="1.0.0",
        runner=lambda fn: fn(),  # run the job at once so a test can read the result
    )
    client = TestClient(app, raise_server_exceptions=False)
    client.world = world
    client.retention = retention
    return client


@pytest.fixture
def token(catalog, issuer):
    made = catalog.post(
        "/v1/tokens",
        json={"name": "t"},
        headers={"Authorization": f"Bearer {issuer.token(username='ada', sub='u1')}"},
    ).json()
    return made["token"]


def headers(token, version="1.2.0"):
    return {"Authorization": f"Bearer {token}", "X-Modelhub-Client": version}


def admin(issuer):
    return {"Authorization": f"Bearer {issuer.token(username='root', sub='u0', admin=True)}"}


def person(issuer):
    return {"Authorization": f"Bearer {issuer.token(username='ada', sub='u1')}"}


def body(bundle):
    return {
        "modelId": bundle.model_id,
        "commit": bundle.commit,
        "bundleName": "b1",
        "bundleDescription": bundle.description_path.read_text(),
        "bundleSignature": bundle.signature_path.read_text(),
        "computer": "pc1",
        "toolVersion": "1.2.0",
        "checkResults": {"ok": True},
    }


def send_pieces(api, token, import_id, bundle):
    for n, path in enumerate(bundle.pieces(), start=1):
        data = path.read_bytes()
        r = api.put(
            f"/v1/imports/{import_id}/pieces/{n}",
            content=data,
            headers={**headers(token), "X-Piece-SHA256": hashlib.sha256(data).hexdigest()},
        )
        assert r.status_code == 204, r.text


# --- the import path ---------------------------------------------------------------------------
def test_the_whole_import_through_the_api(api, token, bundle):
    r = api.post("/v1/imports", json=body(bundle), headers=headers(token))
    assert r.status_code == 201
    job = r.json()
    assert job["state"] == "receiving" and job["missingPieces"] == list(
        range(1, len(bundle.pieces()) + 1)
    )
    send_pieces(api, token, job["importId"], bundle)
    r = api.post(f"/v1/imports/{job['importId']}/start", headers=headers(token))
    assert r.status_code == 202
    done = api.get(f"/v1/imports/{job['importId']}", headers=headers(token)).json()
    assert done["state"] == "done" and done["outcome"] == "imported"
    assert done["progress"]["bytesTotal"] is not None and "error" not in done


def test_importing_the_same_version_again_answers_200_skipped(api, token, bundle):
    job = api.post("/v1/imports", json=body(bundle), headers=headers(token)).json()
    send_pieces(api, token, job["importId"], bundle)
    api.post(f"/v1/imports/{job['importId']}/start", headers=headers(token))
    r = api.post("/v1/imports", json=body(bundle), headers=headers(token))
    assert r.status_code == 200 and r.json()["outcome"] == "skipped"


def test_a_failed_job_carries_the_error_object(api, token, bundle):
    def down(*_args):
        raise UploadNetworkError("network down")

    api.world.gateway.uploader = type("Down", (), {"upload": down})()
    job = api.post("/v1/imports", json=body(bundle), headers=headers(token)).json()
    send_pieces(api, token, job["importId"], bundle)
    api.post(f"/v1/imports/{job['importId']}/start", headers=headers(token))
    got = api.get(f"/v1/imports/{job['importId']}", headers=headers(token)).json()
    assert got["state"] == "failed"
    assert got["error"] == {
        "code": "artifactory_unreachable",
        "message": got["error"]["message"],
        "retryable": True,
    }


def test_cancel_is_204_and_repeats_are_204_too(api, token, bundle):
    job = api.post("/v1/imports", json=body(bundle), headers=headers(token)).json()
    for _ in range(2):
        assert (
            api.delete(f"/v1/imports/{job['importId']}", headers=headers(token)).status_code == 204
        )
    assert api.delete("/v1/imports/nope", headers=headers(token)).status_code == 204
    got = api.get(f"/v1/imports/{job['importId']}", headers=headers(token)).json()
    assert got["state"] == "cancelled"


# --- refusals, in the contract's words ---------------------------------------------------------
def test_error_codes_follow_the_contract(api, token, bundle):
    api.world.keys.revoke(bundle.public_key["fingerprint"], "root")
    r = api.post("/v1/imports", json=body(bundle), headers=headers(token))
    assert r.status_code == 422 and r.json()["code"] == "untrusted_signing_key"
    assert r.json()["retryable"] is False


def test_a_tampered_description_is_bad_signature(api, token, bundle):
    payload = body(bundle)
    doc = json.loads(payload["bundleDescription"])
    doc["stream"]["size"] += 1
    payload["bundleDescription"] = json.dumps(doc)
    r = api.post("/v1/imports", json=payload, headers=headers(token))
    assert r.status_code == 422 and r.json()["code"] == "bad_signature"


def test_the_model_and_commit_must_match_the_signed_description(api, token, bundle):
    payload = body(bundle)
    payload["commit"] = "f" * 40
    r = api.post("/v1/imports", json=payload, headers=headers(token))
    assert r.status_code == 422 and r.json()["code"] == "bundle_invalid"


def test_a_missing_field_is_422_naming_it(api, token, bundle):
    payload = body(bundle)
    del payload["computer"]
    r = api.post("/v1/imports", json=payload, headers=headers(token))
    assert r.status_code == 422 and "computer" in r.json()["message"]


def test_a_wrong_piece_checksum_is_409_piece_mismatch(api, token, bundle):
    job = api.post("/v1/imports", json=body(bundle), headers=headers(token)).json()
    r = api.put(
        f"/v1/imports/{job['importId']}/pieces/1",
        content=b"x",
        headers={**headers(token), "X-Piece-SHA256": "0" * 64},
    )
    assert r.status_code == 409 and r.json()["code"] == "piece_mismatch"
    r = api.put(f"/v1/imports/{job['importId']}/pieces/1", content=b"x", headers=headers(token))
    assert r.status_code == 422


def test_an_oversize_piece_is_413_and_start_with_gaps_is_409(api, token, bundle):
    job = api.post("/v1/imports", json=body(bundle), headers=headers(token)).json()
    first = bundle.pieces()[0].read_bytes()
    r = api.put(
        f"/v1/imports/{job['importId']}/pieces/1",
        content=first + b"!",
        headers={**headers(token), "X-Piece-SHA256": hashlib.sha256(first).hexdigest()},
    )
    assert r.status_code == 413 and r.json()["code"] == "piece_too_large"
    r = api.post(f"/v1/imports/{job['importId']}/start", headers=headers(token))
    assert r.status_code == 409 and r.json()["code"] == "pieces_missing"


# --- who may call ------------------------------------------------------------------------------
def test_import_calls_need_a_personal_token_and_say_nothing_more_when_unknown(api, bundle):
    r = api.post("/v1/imports", json=body(bundle), headers=headers("mhi_unknown"))
    assert r.status_code == 401 and r.json()["code"] == "token_invalid"
    no_token = {"X-Modelhub-Client": "1.2.0"}
    assert api.post("/v1/imports", json=body(bundle), headers=no_token).status_code == 401


def test_a_revoked_token_is_told_to_make_a_new_one(api, token, bundle, catalog, issuer):
    tokens = catalog.get("/v1/tokens", headers=person(issuer)).json()
    items = tokens["items"] if isinstance(tokens, dict) else tokens
    catalog.delete(
        f"/v1/tokens/{items[0].get('tokenId') or items[0]['token_id']}", headers=person(issuer)
    )
    r = api.post("/v1/imports", json=body(bundle), headers=headers(token))
    assert r.status_code == 401 and "new token" in r.json()["message"].lower()


def test_a_personal_token_works_only_under_imports(api, token):
    assert api.get("/v1/retention/settings", headers=headers(token)).status_code == 401
    assert api.get("/v1/trusted-keys", headers=headers(token)).status_code == 401


def test_a_client_that_is_too_old_gets_426_and_nothing_happens(api, token, bundle):
    r = api.post("/v1/imports", json=body(bundle), headers=headers(token, "0.9.0"))
    assert r.status_code == 426 and r.json()["minimumCliVersion"] == "1.0.0"
    missing = {"Authorization": f"Bearer {token}"}
    assert api.post("/v1/imports", json=body(bundle), headers=missing).status_code == 426


def test_only_the_owner_can_read_a_job(api, token, bundle, catalog, issuer):
    job = api.post("/v1/imports", json=body(bundle), headers=headers(token)).json()
    other = catalog.post(
        "/v1/tokens",
        json={"name": "o"},
        headers={"Authorization": f"Bearer {issuer.token(username='bob', sub='u2')}"},
    ).json()["token"]
    assert api.get(f"/v1/imports/{job['importId']}", headers=headers(other)).status_code == 404


def test_the_health_checks_need_no_credential(api):
    assert api.get("/healthz").status_code == 200
    assert api.get("/readyz").status_code == 200


# --- retention and keys ------------------------------------------------------------------------
def test_retention_settings_any_person_reads_only_an_administrator_changes(api, issuer):
    assert api.get("/v1/retention/settings", headers=person(issuer)).json()["periodDays"] == 365
    r = api.put("/v1/retention/settings", json={"periodDays": 30}, headers=person(issuer))
    assert r.status_code == 403 and r.json()["code"] == "forbidden"
    r = api.put("/v1/retention/settings", json={"periodDays": 30}, headers=admin(issuer))
    assert r.status_code == 200 and r.json()["periodDays"] == 30
    r = api.put("/v1/retention/settings", json={"periodDays": 0}, headers=admin(issuer))
    assert r.status_code == 422


def test_due_and_decisions(api, issuer, world):
    api.retention.set_period(1, "root")
    rec = record(importedAt="2020-01-01T00:00:00Z")
    world.catalog.put_version("acme/tiny", "1" * 40, rec, DOCS)
    assert api.get("/v1/retention/due", headers=person(issuer)).status_code == 403
    due = api.get("/v1/retention/due", headers=admin(issuer)).json()
    assert [d["commit"] for d in due["items"]] == ["1" * 40]
    r = api.post(
        "/v1/retention/decisions",
        json={"modelId": "acme/tiny", "commit": "1" * 40, "decision": "keep"},
        headers=person(issuer),
    )
    assert r.status_code == 403
    r = api.post(
        "/v1/retention/decisions",
        json={"modelId": "acme/tiny", "commit": "1" * 40, "decision": "keep"},
        headers=admin(issuer),
    )
    assert r.status_code == 200 and r.json()["outcome"] == "kept"
    listed = api.get("/v1/retention/decisions", headers=person(issuer)).json()
    assert listed["items"][0]["decidedBy"] == "root"
    r = api.post(
        "/v1/retention/decisions",
        json={"modelId": "acme/tiny", "commit": "2" * 40, "decision": "keep"},
        headers=admin(issuer),
    )
    assert r.status_code == 409


def test_trusted_keys_list_add_and_remove(api, issuer, bundle, tmp_path):
    from modelhub_testkit.bundles import make_bundle

    new = make_bundle(tmp_path / "n", model_id="org/n")
    doc = new.public_key
    payload = {
        "publicKey": json.dumps(doc),
        "typedFingerprint": doc["fingerprint"],
        "name": "second",
    }
    assert api.post("/v1/trusted-keys", json=payload, headers=person(issuer)).status_code == 403
    r = api.post(
        "/v1/trusted-keys", json={**payload, "typedFingerprint": "wrong"}, headers=admin(issuer)
    )
    assert r.status_code == 422 and r.json()["code"] == "fingerprint_mismatch"
    r = api.post("/v1/trusted-keys", json=payload, headers=admin(issuer))
    assert r.status_code == 201 and r.json()["fingerprint"] == doc["fingerprint"]
    assert api.post("/v1/trusted-keys", json=payload, headers=admin(issuer)).status_code == 409
    listed = api.get("/v1/trusted-keys", headers=admin(issuer)).json()["items"]
    mine = next(k for k in listed if k["fingerprint"] == doc["fingerprint"])
    assert mine["name"] == "second" and mine["status"] == "active"
    for _ in range(2):
        r = api.delete(f"/v1/trusted-keys/{mine['keyId']}", headers=admin(issuer))
        assert r.status_code == 204
    again = api.get("/v1/trusted-keys", headers=admin(issuer)).json()["items"]
    assert next(k for k in again if k["keyId"] == mine["keyId"])["status"] == "revoked"
    assert api.delete("/v1/trusted-keys/nope", headers=admin(issuer)).status_code == 204
