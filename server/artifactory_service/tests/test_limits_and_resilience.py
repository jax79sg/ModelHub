"""Speed, stops, outages, memory, secrets, permissions and sockets of the import service
(loop-back 2).

Checks NFR2.1, NFR7.7, NFR4.1, NFR4.2, NFR3.2, NFR7.3, NFR5.2, NFR5.5 and NFR8.1 of the
artifactory-service unit. Nothing here weakens a target.
"""

import hashlib
import ipaddress
import logging
import os
import socket
import stat
import subprocess
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import pytest
from conftest import trust
from fastapi.testclient import TestClient
from modelhub_artifactory_service import importer as importer_module
from modelhub_artifactory_service.app import create_app
from modelhub_artifactory_service.catalog_client import CatalogUnavailable
from modelhub_artifactory_service.gateway import Gateway, JfUploader
from modelhub_artifactory_service.retention import Retention
from modelhub_testkit.bundles import make_bundle
from modelhub_testkit.relay import Relay
from test_api import admin, body, headers, send_pieces
from test_api import api as _api
from test_api import token as _token
from test_importer import create, run_import, send_all

api, token = _api, _token  # re-used fixtures


def p95(times: list[float]) -> float:
    times = sorted(times)
    return times[int(len(times) * 0.95) - 1]


# --- NFR2.1 and NFR7.7: short calls, alone and 20 at once -----------------------------------------
def test_short_calls_answer_under_a_second_at_the_95th_percentile(api, token, issuer, bundle):
    job = api.post("/v1/imports", json=body(bundle), headers=headers(token)).json()
    calls = [
        lambda: api.get(f"/v1/imports/{job['importId']}", headers=headers(token)),
        lambda: api.get("/v1/trusted-keys", headers=admin(issuer)),
        lambda: api.get("/v1/retention/due", headers=admin(issuer)),
        lambda: api.get("/v1/retention/settings", headers=admin(issuer)),
    ]
    times = []
    for i in range(100):
        began = time.perf_counter()
        assert calls[i % len(calls)]().status_code == 200
        times.append(time.perf_counter() - began)
    assert p95(times) < 1.0


def test_twenty_people_at_once_stay_within_the_same_target(api, token, issuer, bundle):
    job = api.post("/v1/imports", json=body(bundle), headers=headers(token)).json()
    paths = [
        ("/v1/trusted-keys", admin(issuer)),
        ("/v1/retention/due", admin(issuer)),
        (f"/v1/imports/{job['importId']}", headers(token)),
    ]

    def one(i: int) -> float:
        path, h = paths[i % len(paths)]
        began = time.perf_counter()
        assert api.get(path, headers=h).status_code == 200
        return time.perf_counter() - began

    with ThreadPoolExecutor(max_workers=20) as pool:
        times = list(pool.map(one, range(100)))
    assert p95(times) < 1.0


# --- NFR4.1: a piece is acknowledged promptly ----------------------------------------------------
def test_a_piece_is_acknowledged_with_under_100_ms_of_overhead(world, bundle):
    job = create(world, bundle)
    pieces = [(n, p.read_bytes()) for n, p in enumerate(bundle.pieces(), start=1)]
    times = []
    for i in range(60):
        number, data = pieces[i % len(pieces)]
        began = time.perf_counter()
        world.put_piece(
            job["importId"], "u1", number, _stream(data), hashlib.sha256(data).hexdigest()
        )
        times.append(time.perf_counter() - began)
    assert p95(times) < 0.100


def _stream(data: bytes):
    import io

    return io.BytesIO(data)


# --- NFR4.2: stop at each state, run again --------------------------------------------------------
class Killed(BaseException):
    """The process died here (not an error the service could catch)."""


def _after_real(fn, then):
    def go(*a, **k):
        fn(*a, **k)
        then()

    return go


def _die(*a, **k):
    raise Killed


@pytest.mark.parametrize(
    "where", ["verifying", "unpacking", "before-upload", "after-upload", "recording"]
)
def test_an_import_stopped_at_any_state_runs_again_to_a_correct_result(
    world, bundle, monkeypatch, where
):
    job = create(world, bundle)
    send_all(world, job, bundle)
    world.start(job["importId"], "u1")
    with monkeypatch.context() as m:
        if where == "verifying":
            m.setattr(importer_module.verify, "verify_bundle", _die)
        elif where == "unpacking":
            m.setattr(importer_module.unpack, "rebuild_into", _die)
        elif where == "before-upload":
            m.setattr(world.gateway.uploader, "upload", _die)
        elif where == "after-upload":
            real = world.gateway.uploader.upload
            m.setattr(world.gateway.uploader, "upload", _after_real(real, _die))
        else:
            m.setattr(world.catalog, "put_version", _die)
        with pytest.raises(Killed):
            world.run(job["importId"])
    # the service starts again: what was running is failed as interrupted, never complete
    assert world.sweep_restart() == 1
    stopped = world.get(job["importId"], "u1")
    assert stopped["state"] == "failed" and stopped["error"]["retryable"] is True
    assert world.catalog.get_version(bundle.model_id, bundle.commit) in (None, {}) or (
        where == "recording"
    )
    again = run_import(world, bundle)
    assert again["state"] == "done" and again["outcome"] in ("imported", "completed")
    listing = world.gateway.list_version(bundle.model_id, bundle.commit)
    assert listing.state == "present" and "model.safetensors" in listing.files
    assert world.catalog.get_version(bundle.model_id, bundle.commit)["state"] == "imported"
    assert not (world.work / job["importId"]).exists()


# --- NFR3.2: Artifactory or the Catalog away, then back -------------------------------------------
def test_with_artifactory_away_imports_fail_retryable_the_service_stays_up_and_it_recovers(
    world, bundle, stand_in, issuer
):
    from modelhub_common.health import HealthCheck

    parts = urlparse(stand_in.url)
    relay = Relay(parts.hostname, parts.port)
    relay.start()
    world.gateway = Gateway(
        f"http://127.0.0.1:{relay.port}", stand_in.repo_key, stand_in.token, connect_timeout=1
    )
    app = create_app(
        world,
        Retention(world.pool, world.gateway, world.catalog, world.clock),
        world.keys,
        world.catalog,
        jwks_fetch=issuer.jwks,
        issuer=issuer.issuer,
        audience=issuer.audience,
        runner=lambda fn: fn(),
        extra_checks=[HealthCheck("artifactory", world.gateway.ping, cache_seconds=0)],
    )
    client = TestClient(app, raise_server_exceptions=False)
    try:
        assert client.get("/readyz").json()["checks"]["artifactory"] == "ok"
        relay.stop()
        job = create(world, bundle)
        send_all(world, job, bundle)
        world.start(job["importId"], "u1")
        world.run(job["importId"])
        failed = world.get(job["importId"], "u1")
        assert failed["state"] == "failed" and failed["error"]["retryable"] is True
        ready = client.get("/readyz")
        assert ready.status_code == 200  # degraded, not down
        assert ready.json()["checks"]["artifactory"] == "down"
        assert client.get("/healthz").status_code == 200
        relay.start()
        assert client.get("/readyz").json()["checks"]["artifactory"] == "ok"
        again = run_import(world, bundle)
        assert again["state"] == "done"
    finally:
        relay.close()


def test_with_the_catalog_away_imports_fail_retryable_and_succeed_when_it_returns(
    world, bundle, monkeypatch
):
    def away(*a, **k):
        raise CatalogUnavailable("the Catalog could not be reached")

    with monkeypatch.context() as m:
        m.setattr(world.catalog, "put_version", away)
        job = create(world, bundle)
        send_all(world, job, bundle)
        world.start(job["importId"], "u1")
        world.run(job["importId"])
        failed = world.get(job["importId"], "u1")
        assert failed["state"] == "failed" and failed["error"]["retryable"] is True
        assert failed["error"]["code"] == "catalog_unavailable"
    assert run_import(world, bundle)["state"] == "done"


# --- NFR7.3: memory for any file size ----------------------------------------------------------------
def test_a_large_bundle_is_handled_with_memory_far_below_its_size(tmp_path, world, stand_in):
    size = 48 * 1024 * 1024
    weights = os.urandom(1024 * 1024) * 48
    big = make_bundle(
        tmp_path / "big",
        model_id="org/big",
        files={"model.safetensors": weights, "config.json": b"{}"},
        piece_size=8 * 1024 * 1024,
    )
    trust(world.keys, big, "big")
    tracemalloc.start()
    try:
        job = run_import(world, big)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert job["state"] == "done"
    assert len(weights) == size
    assert peak < 8 * 1024**3  # the planning figure
    assert peak < size  # and in fact far below the size of what was imported


# --- NFR5.2: the credential in no log and no process listing -------------------------------------
def test_the_credential_is_in_no_log_at_any_level(world, bundle, caplog):
    caplog.set_level(logging.DEBUG)
    run_import(world, bundle)
    text = " ".join(str(r.__dict__) + r.getMessage() for r in caplog.records)
    assert world.gateway._token not in text


@pytest.mark.skipif(sys.platform == "win32", reason="needs a shell script as the upload tool")
def test_the_upload_tool_sees_the_credential_only_in_its_environment(tmp_path):
    secret = "tok-" + os.urandom(8).hex()
    listing = tmp_path / "listing.txt"
    fake = tmp_path / "jf"
    fake.write_text(
        f'#!/bin/sh\nps -o args= -p $$ > "{listing}"\necho "$*" >> "{listing}"\nexit 0\n',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    folder = tmp_path / "files"
    folder.mkdir()
    JfUploader("http://127.0.0.1:1", "models-hf", secret, jf_path=str(fake)).upload(
        folder, "org/tiny", "a" * 40
    )
    seen = listing.read_text(encoding="utf-8")
    assert "upload" in seen and secret not in seen


# --- NFR5.5: owner-only permissions on the work folder -----------------------------------------
@pytest.mark.skipif(sys.platform == "win32", reason="no owner-only mode bits on Windows")
def test_the_work_folder_and_each_import_folder_are_owner_only(world, bundle):
    job = create(world, bundle)
    for folder in (world.work, world.work / job["importId"], world.work / job["importId"] / "in"):
        assert stat.S_IMODE(folder.stat().st_mode) & 0o077 == 0, folder


# --- NFR8.1: nothing leaves the machine ----------------------------------------------------------
def test_with_other_sockets_blocked_a_full_import_still_works(world, bundle, monkeypatch):
    refused = []
    real = socket.socket.connect

    def guarded(self, address):
        host = address[0] if isinstance(address, tuple) else None
        if host is not None and not ipaddress.ip_address(socket.gethostbyname(host)).is_loopback:
            refused.append(address)
            raise OSError(f"blocked: {address}")
        return real(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)
    assert run_import(world, bundle)["state"] == "done"
    assert refused == []


_ = (send_pieces, subprocess)


# --- platform NFR7.2: the documented free-space minimum is checked at start too -------------------
def test_an_import_is_not_started_when_the_space_has_gone_since_it_was_created(world, bundle):
    import json

    from modelhub_artifactory_service.importer import ServiceError

    size = json.loads(bundle.description_path.read_text())["stream"]["size"]
    job = create(world, bundle)
    send_all(world, job, bundle)
    world.free_bytes = lambda path: size + size // 10 - 1  # one byte short of the sizes plus 10%
    with pytest.raises(ServiceError) as err:
        world.start(job["importId"], "u1")
    assert err.value.status == 507 and err.value.retryable is True
    assert world.get(job["importId"], "u1")["state"] == "receiving"  # still open, nothing lost
    world.free_bytes = lambda path: size + size // 10
    assert world.start(job["importId"], "u1")["state"] == "verifying"
