"""Event codes, speed at size, outage, stop and hostile input (loop-back 2).

Checks NFR6.5, NFR2.1, NFR2.2, NFR2.4, NFR2.5, NFR4.1, NFR4.3, NFR4.4, NFR5.7, NFR7.1, NFR7.3,
NFR7.4 and NFR8.1 of the catalog unit. Nothing here weakens a target.
"""

import copy
import ipaddress
import json
import logging
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest
from conftest import C1, PEPPER, make_docs, make_record
from fastapi.testclient import TestClient
from modelhub_catalog import db
from modelhub_catalog.app import create_app
from modelhub_catalog.store import CatalogStore, Document, StoreFailed
from modelhub_testkit.issuer import FakeIssuer
from psycopg.conninfo import conninfo_to_dict
from test_api import person, put_version, service
from test_list_speed import fill

COMMITS = [f"{i:040x}" for i in range(1, 11)]


@pytest.fixture
def issuer():
    return FakeIssuer()


@pytest.fixture
def client(store, issuer):
    return TestClient(
        create_app(store, jwks_fetch=issuer.jwks, issuer=issuer.issuer, audience=issuer.audience),
        raise_server_exceptions=False,
    )


def fill_versions(url: str, per_model: int = 10) -> None:
    """Give every filled model `per_model` stored versions (1,000 models, 10,000 versions)."""
    with psycopg.connect(url) as conn:
        conn.execute(
            "insert into model_versions (model_key, commit, state, captured_at, record_checksum, "
            "record_format, imported_at, imported_by_id, imported_by_name) "
            "select m.model_key, lpad(to_hex(v), 40, '0'), 'imported', now(), 'x', 1, now(), 'u1', "
            "'ada' from models m, generate_series(1, %s) v",
            (per_model,),
        )
        conn.commit()


# --- NFR6.5: the fixed event codes -----------------------------------------------------------
def test_every_fixed_event_code_is_logged(store, client, issuer, caplog, fresh_database):
    caplog.set_level(logging.INFO, logger="modelhub")
    db.migrate(fresh_database)  # nothing pending: no event
    with psycopg.connect(fresh_database) as conn:
        conn.execute("drop table schema_steps")  # make the step run again on a copy of the schema
        conn.execute("drop schema public cascade; create schema public")
        conn.commit()
    db.migrate(fresh_database)
    assert put_version(client, issuer).status_code == 201
    changed = copy.deepcopy(make_record())
    changed["version"]["downloads"] = 5
    assert put_version(client, issuer, record=changed).status_code == 409  # record_conflict
    made = client.post("/v1/tokens", json={"name": "t"}, headers=person(issuer, "ada"))
    assert made.status_code == 201
    client.delete(f"/v1/tokens/{made.json()['tokenId']}", headers=person(issuer, "ada"))
    removed = client.post(
        f"/v1/models/acme/tiny/versions/{C1}/removal",
        headers=service(issuer),
        json={"removedBy": "root"},
    )
    assert removed.status_code == 200

    def broken(*a, **k):
        raise psycopg.OperationalError("down")

    store._refresh_summary = broken
    other = copy.deepcopy(make_record("acme/other", "2" * 40))
    assert put_version(client, issuer, "acme/other", "2" * 40, record=other).status_code == 500
    codes = {getattr(r, "event", None) for r in caplog.records}
    assert {
        "store_failed",
        "record_conflict",
        "token_made",
        "token_revoked",
        "version_removed",
        "migration_applied",
    } <= codes


# --- NFR2.1, NFR7.1, NFR7.3: the list at size, 20 at once --------------------------------------
def test_the_list_meets_its_target_at_1000_models_10000_versions_with_20_at_once(
    store, fresh_database
):
    fill(fresh_database)
    fill_versions(fresh_database)
    queries = [{}, {"task": "text-generation"}, {"sort": "likes"}, {"q": "quantized"}, {"page": 3}]

    def one(i: int) -> float:
        began = time.perf_counter()
        store.list_models(queries[i % len(queries)])
        return time.perf_counter() - began

    with ThreadPoolExecutor(max_workers=20) as pool:
        times = list(pool.map(one, range(100)))
    assert sum(t < 1.0 for t in times) >= 95


# --- NFR2.2: the list reads no document table ------------------------------------------------
def test_a_list_reads_only_the_summary_table(store, fresh_database, monkeypatch):
    fill(fresh_database, 50)
    seen: list[str] = []
    real = psycopg.Connection.execute

    def spy(self, query, *args, **kw):
        seen.append(query if isinstance(query, str) else str(query))
        return real(self, query, *args, **kw)

    monkeypatch.setattr(psycopg.Connection, "execute", spy)
    store.list_models({"q": "quantized", "sort": "likes", "task": "text-generation"})
    text = " ".join(seen).lower()
    assert "model_summary" in text
    for table in (
        "documents",
        "version_files",
        "model_versions",
        "import_records",
        "personal_tokens",
    ):
        assert table not in text, table


# --- NFR2.4: one record at size -------------------------------------------------------------
def test_one_model_or_version_answers_under_300_ms_at_the_95th_percentile(
    store, client, issuer, fresh_database
):
    fill(fresh_database)
    fill_versions(fresh_database)
    with psycopg.connect(fresh_database) as conn:
        key = conn.execute("select model_key from models order by model_key limit 1").fetchone()[0]
    headers = person(issuer)
    times = []
    for i in range(100):
        began = time.perf_counter()
        path = f"/v1/models/{key}" if i % 2 == 0 else f"/v1/models/{key}/versions/{1:040x}"
        assert client.get(path, headers=headers).status_code == 200
        times.append(time.perf_counter() - began)
    times.sort()
    assert times[94] < 0.3


# --- NFR2.5: the first byte of a 16 MiB document ----------------------------------------------
def test_a_16_mib_document_starts_arriving_in_under_a_second(store, client, issuer):
    big = Document("response", "big.json", "application/json", b"x" * (16 * 1024 * 1024))
    store.put_version("acme/tiny", C1, copy.deepcopy(make_record()), [*make_docs(), big])
    began = time.perf_counter()
    with client.stream(
        "GET",
        f"/v1/models/acme/tiny/versions/{C1}/documents/response/big.json",
        headers=person(issuer),
    ) as r:
        assert r.status_code == 200
        first = next(r.iter_bytes())
        elapsed = time.perf_counter() - began
    assert first and elapsed < 1.0


# --- NFR4.1: a big first store, and an identical repeat --------------------------------------
def test_a_version_of_10000_files_and_the_most_documents_allowed_stores_in_under_a_minute(store):
    record = make_record("acme/big", C1)
    record["version"]["files"] = [
        {
            "path": f"shards/part-{i:05d}.bin",
            "size_bytes": 1000 + i,
            "sha256": f"{i:064x}",
            "file_type": "bin",
            "safety_scan": "safe",
            "downloaded": False,
        }
        for i in range(10_000)
    ]
    docs = [
        Document("response", f"doc-{n}.json", "application/json", bytes([65 + n]) * (16 * 1024**2))
        for n in range(4)
    ]  # 64 MiB, the most a version may hold (NFR7.5)
    began = time.perf_counter()
    assert store.put_version("acme/big", C1, copy.deepcopy(record), docs).status == "created"
    first = time.perf_counter() - began
    began = time.perf_counter()
    assert store.put_version("acme/big", C1, copy.deepcopy(record), docs).status == "unchanged"
    repeat = time.perf_counter() - began
    assert first < 60 and repeat < 1.0


# --- NFR4.3: the database goes away and comes back ----------------------------------------------
class Relay:
    """A TCP relay in front of PostgreSQL that can be switched off and on.

    While off it accepts a connection and drops it at once, so the service sees a database that
    is away; switched on, it passes connections through again.
    """

    def __init__(self, host: str, port: int) -> None:
        self.target = (host, port)
        self.up = False
        self.live: list[socket.socket] = []
        self.server = socket.socket()
        self.server.bind(("127.0.0.1", 0))
        self.server.listen(50)
        self.port = self.server.getsockname()[1]
        threading.Thread(target=self._accept, daemon=True).start()

    def start(self) -> None:
        self.up = True

    def stop(self) -> None:
        self.up = False
        for s in self.live:
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            s.close()
        self.live.clear()

    def close(self) -> None:
        self.stop()
        self.server.close()

    def _accept(self) -> None:
        while True:
            try:
                client, _ = self.server.accept()
            except OSError:
                return
            if not self.up:
                client.close()
                continue
            try:
                upstream = socket.create_connection(self.target, timeout=5)
            except OSError:
                client.close()
                continue
            self.live += [client, upstream]
            for a, b in ((client, upstream), (upstream, client)):
                threading.Thread(target=self._pipe, args=(a, b), daemon=True).start()

    @staticmethod
    def _pipe(src: socket.socket, dst: socket.socket) -> None:
        try:
            while data := src.recv(65536):
                dst.sendall(data)
        except OSError:
            pass
        finally:
            for s in (src, dst):
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass


def wait_for(client, status: int, seconds: float = 45) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if client.get("/readyz").status_code == status:
            return
        time.sleep(0.5)
    raise AssertionError(f"/readyz never answered {status}")


def test_with_the_database_down_it_answers_503_and_recovers_by_itself(fresh_database, issuer):
    info = conninfo_to_dict(fresh_database)
    db.migrate(fresh_database)
    relay = Relay(info.get("host") or "127.0.0.1", int(info.get("port") or 5432))
    relay.start()
    via = psycopg.conninfo.make_conninfo(fresh_database, host="127.0.0.1", port=relay.port)
    store = CatalogStore(via, pepper=PEPPER, pool_size=3, reconnect_timeout_s=6)
    client = TestClient(
        create_app(store, jwks_fetch=issuer.jwks, issuer=issuer.issuer, audience=issuer.audience),
        raise_server_exceptions=False,
    )
    try:
        assert client.get("/readyz").status_code == 200
        relay.stop()
        wait_for(client, 503)  # the ready answer is cached for up to 10 seconds
        down = client.get("/v1/models", headers=person(issuer))
        assert down.status_code == 503, down.text
        assert client.get("/healthz").status_code == 200  # still alive, only not ready
        relay.start()
        wait_for(client, 200, 90)
        assert client.get("/v1/models", headers=person(issuer)).status_code == 200
    finally:
        relay.close()
        store.close()


# --- NFR4.4: stop grace and rollback --------------------------------------------------------------
def test_the_server_is_started_with_a_30_second_stop_grace(monkeypatch, fresh_database, tmp_path):
    import uvicorn
    from modelhub_catalog import main

    seen = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: seen.update(kw))
    monkeypatch.setattr(main, "load_config", lambda *a, **k: ({}, {}))
    monkeypatch.setattr(main, "configure_logging", lambda *a, **k: None)
    fake_app = type("A", (), {"state": type("S", (), {"settings": {"MODELHUB_PORT": 1}})()})()
    monkeypatch.setattr(main, "build_app", lambda: fake_app)
    assert main.main() == 0
    assert seen["timeout_graceful_shutdown"] == 30


def test_a_store_cut_off_part_way_leaves_nothing_behind(store, fresh_database):
    def die_midway(conn, key):
        with psycopg.connect(fresh_database, autocommit=True) as admin:
            pid = conn.execute("select pg_backend_pid() as p").fetchone()["p"]
            admin.execute("select pg_terminate_backend(%s)", (pid,))
        conn.execute("select 1")

    store._refresh_summary = die_midway
    with pytest.raises(StoreFailed):
        store.put_version("acme/tiny", C1, copy.deepcopy(make_record()), make_docs())
    with psycopg.connect(fresh_database) as conn:
        for table in ("models", "model_versions", "version_files", "documents", "import_records"):
            assert conn.execute(f"select count(*) from {table}").fetchone()[0] == 0, table


# --- NFR7.4: a second copy ------------------------------------------------------------------------
def test_a_second_copy_starts_on_the_same_database_and_sees_the_same_data(
    store, client, issuer, fresh_database
):
    assert put_version(client, issuer).status_code == 201
    db.migrate(fresh_database)  # the second copy's start-up: nothing to redo, no error
    second = CatalogStore(fresh_database, pepper=PEPPER)
    other = TestClient(
        create_app(second, jwks_fetch=issuer.jwks, issuer=issuer.issuer, audience=issuer.audience)
    )
    try:
        assert other.get("/v1/models/acme/tiny", headers=person(issuer)).status_code == 200
        assert put_version(other, issuer, "acme/two", "2" * 40).status_code == 201
        assert client.get("/v1/models/acme/two", headers=person(issuer)).status_code == 200
    finally:
        second.close()


# --- NFR5.7: hostile text in every filter ---------------------------------------------------------
HOSTILE = ["'; drop table models; --", "' or '1'='1", "%' or 1=1 --", '"; select pg_sleep(5); --']


@pytest.mark.parametrize(
    "name",
    [
        "task",
        "library",
        "license",
        "importedBy",
        "importedByName",
        "language",
        "parameters",
        "importedFrom",
        "importedTo",
        "q",
        "sort",
        "page",
        "pageSize",
        "showRemoved",
    ],
)
def test_hostile_text_in_a_filter_changes_nothing(store, client, issuer, put, fresh_database, name):
    put()
    for text in HOSTILE:
        r = client.get("/v1/models", params={name: text}, headers=person(issuer))
        assert r.status_code in (200, 422), (name, text, r.status_code)
        if r.status_code == 200:
            assert r.json()["total"] in (0, 1)
    with psycopg.connect(fresh_database) as conn:
        assert conn.execute("select count(*) from models").fetchone()[0] == 1


@pytest.mark.parametrize("text", HOSTILE)
def test_hostile_text_in_a_path_is_a_plain_not_found(client, issuer, put, text):
    put()
    for path in (f"/v1/models/acme/{text}", f"/v1/models/acme/tiny/versions/{text}"):
        assert client.get(path, headers=person(issuer)).status_code in (404, 422)


# --- NFR8.1: nothing but the database and the key address -------------------------------------------
def test_with_other_sockets_blocked_the_catalog_still_serves(store, client, issuer, monkeypatch):
    refused = []
    real = socket.socket.connect

    def guarded(self, address):
        host = address[0] if isinstance(address, tuple) else None
        if host is not None and not ipaddress.ip_address(socket.gethostbyname(host)).is_loopback:
            refused.append(address)
            raise OSError(f"blocked: {address}")
        return real(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)
    assert put_version(client, issuer).status_code == 201
    assert client.get("/v1/models", headers=person(issuer)).status_code == 200
    assert client.get("/readyz").status_code == 200
    assert refused == []
    _ = json
