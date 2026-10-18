"""Readiness that says when Artifactory or the Catalog is down, and the fixed event codes (NFR6.2, NFR6.5)."""

import json
import logging
import uuid

import pytest
from conftest import trust
from fastapi.testclient import TestClient
from modelhub_artifactory_service.app import create_app
from modelhub_artifactory_service.gateway import Gateway
from modelhub_artifactory_service.retention import Retention
from modelhub_stand_in.server import StandIn
from test_importer import create, run_import, send_all

C1 = "1" * 40
EVENTS = {
    "import_created",
    "import_skipped",
    "import_done",
    "import_failed",
    "import_cancelled",
    "key_added",
    "key_revoked",
    "retention_decided",
}


def events(caplog) -> list[str]:
    return [
        getattr(r, "event", None) for r in caplog.records if getattr(r, "event", None) in EVENTS
    ]


@pytest.fixture(autouse=True)
def _log_level(caplog):
    caplog.set_level(logging.INFO, logger="modelhub")


# --- ping ------------------------------------------------------------------------------------
def test_the_gateway_pings_artifactory_with_the_credential(world):
    assert world.gateway.ping() is True


def test_the_gateway_ping_is_false_when_artifactory_is_down_or_refuses(tmp_path):
    with StandIn(token="svc-token-1", workdir=tmp_path / "si") as s:
        down_url, key = s.url, s.repo_key
        wrong = Gateway(s.url, key, "wrong-token")
        assert wrong.ping() is False
    assert Gateway(down_url, key, "svc-token-1").ping() is False


def test_the_catalog_client_pings_the_catalog_without_a_token(world):
    assert world.catalog.ping() is True


# --- readiness -------------------------------------------------------------------------------
@pytest.fixture
def app_client(world, issuer):
    from modelhub_common.health import HealthCheck

    def make(gateway=None, catalog=None):
        app = create_app(
            world,
            Retention(world.pool, world.gateway, world.catalog, world.clock),
            world.keys,
            world.catalog,
            jwks_fetch=issuer.jwks,
            issuer=issuer.issuer,
            audience=issuer.audience,
            runner=lambda fn: fn(),
            extra_checks=[
                HealthCheck("artifactory", (gateway or world.gateway).ping),
                HealthCheck("catalog", (catalog or world.catalog).ping),
            ],
        )
        return TestClient(app)

    return make


def test_ready_is_ok_when_everything_answers(app_client):
    body = app_client().get("/readyz").json()
    assert body["status"] == "ok" and body["checks"] == {
        "database": "ok",
        "artifactory": "ok",
        "catalog": "ok",
    }


def test_ready_is_degraded_not_down_when_artifactory_is_unreachable(app_client, world):
    dead = Gateway("http://127.0.0.1:9", "hf-local", "t", connect_timeout=0.2)
    r = app_client(gateway=dead).get("/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "degraded" and r.json()["checks"]["artifactory"] == "down"


# --- the fixed event codes -------------------------------------------------------------------
def test_a_full_import_logs_created_then_done(world, bundle, caplog):
    run_import(world, bundle)
    assert events(caplog) == ["import_created", "import_done"]


def test_a_skipped_import_logs_skipped(world, bundle, caplog):
    run_import(world, bundle)
    caplog.clear()
    create(world, bundle, ("u2", "bob"))
    assert events(caplog) == ["import_skipped"]


def test_a_failed_import_logs_failed_with_its_code(world, bundle, caplog):
    job = create(world, bundle)
    send_all(world, job, bundle)
    victim = next((world.work / job["importId"] / "in").glob("*.part-*"))
    victim.write_bytes(victim.read_bytes()[:-1] + b"?")
    world.start(job["importId"], "u1")
    world.run(job["importId"])
    failed = [r for r in caplog.records if getattr(r, "event", "") == "import_failed"]
    assert len(failed) == 1 and failed[0].code == "piece-damaged"


def test_a_cancelled_import_logs_cancelled(world, bundle, caplog):
    job = create(world, bundle)
    caplog.clear()
    world.cancel(job["importId"], "u1")
    assert events(caplog) == ["import_cancelled"]


def test_keys_and_decisions_log_their_codes(app_client, issuer, bundle, tmp_path, caplog):
    from modelhub_testkit.bundles import make_bundle

    client = app_client()
    admin = {"Authorization": f"Bearer {issuer.token(username='root', sub='u0', admin=True)}"}
    new = make_bundle(tmp_path / "n", model_id="org/n")
    doc = new.public_key
    added = client.post(
        "/v1/trusted-keys",
        json={"publicKey": json.dumps(doc), "typedFingerprint": doc["fingerprint"], "name": "k"},
        headers=admin,
    )
    assert added.status_code == 201
    client.delete(f"/v1/trusted-keys/{added.json()['keyId']}", headers=admin)
    assert events(caplog) == ["key_added", "key_revoked"]


def test_a_retention_decision_logs_its_code(world, bundle, caplog):
    from modelhub_artifactory_service.retention import Retention

    run_import(world, bundle)
    caplog.clear()
    Retention(world.pool, world.gateway, world.catalog, world.clock).decide(
        bundle.model_id, bundle.commit, "keep", "u0", "root"
    )
    assert events(caplog) == ["retention_decided"]


def test_no_event_carries_a_secret_or_a_token(world, bundle, caplog):
    secret = "s" + uuid.uuid4().hex
    world.gateway._token = secret
    run_import(world, bundle)
    text = " ".join(str(r.__dict__) for r in caplog.records)
    assert secret not in text and "mhi_" not in text and "Bearer" not in text


_ = trust
