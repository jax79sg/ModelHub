"""Speed, size, concurrency and hygiene targets of the stand-in (loop-back 2).

Each test names the target it checks (NFR6.1, NFR9.1 to NFR9.3, NFR7.1, NFR7.2, NFR5.3, NFR5.6,
NFR8.1 of the artifactory-stand-in unit). Nothing here weakens a target.
"""

import ipaddress
import json
import logging
import socket
import subprocess
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest
from modelhub_stand_in.server import StandIn
from modelhub_stand_in.store import StoredFile, Version

TOKEN = "limits-token-7c1"
SRC = Path(__file__).parents[1] / "src" / "modelhub_stand_in"


def auth(stand_in):
    return {"Authorization": f"Bearer {stand_in.token}"}


# --- NFR9.1, NFR9.2: speed ----------------------------------------------------------------------
def test_it_starts_and_answers_its_first_call_in_under_two_seconds(tmp_path):
    began = time.perf_counter()
    with StandIn(token=TOKEN, workdir=tmp_path) as s:
        r = httpx.get(f"{s.url}/artifactory/api/storage/models-hf", headers=auth(s))
        elapsed = time.perf_counter() - began
    assert r.status_code == 200
    assert elapsed < 2.0


def test_calls_that_move_no_content_have_a_95th_percentile_under_50_ms(stand_in):
    with httpx.Client(headers=auth(stand_in)) as client:
        url = f"{stand_in.url}/artifactory/api/storage/models-hf"
        client.get(url)  # warm up the connection
        times = []
        for _ in range(200):
            began = time.perf_counter()
            assert client.get(url).status_code == 200
            times.append(time.perf_counter() - began)
    times.sort()
    assert times[int(len(times) * 0.95) - 1] < 0.050


# --- NFR9.3: a declared file of any size ---------------------------------------------------------
def test_a_one_tebibyte_declaration_is_accepted_within_500_megabytes(stand_in):
    h = auth(stand_in)
    tib = 2**40
    oid = "a" * 64
    body = (
        json.dumps({"key": "header", "value": {"summary": "declare"}})
        + "\n"
        + json.dumps({"key": "lfsFile", "value": {"path": "big.bin", "oid": oid, "size": tib}})
        + "\n"
    )
    tracemalloc.start()
    try:
        r = httpx.post(
            f"{stand_in.hf_endpoint}/api/models/acme/huge/commit/main", content=body, headers=h
        )
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert r.status_code == 200
    assert peak < 500 * 1024 * 1024
    listed = httpx.get(
        f"{stand_in.url}/artifactory/api/storage/models-hf/acme/huge",
        params={"list": ""},
        headers=h,
    ).json()
    assert [f["size"] for f in listed["files"]] == [tib]


# --- NFR7.1: many versions -----------------------------------------------------------------------
def test_it_holds_a_thousand_versions_and_a_version_of_ten_thousand_files(stand_in):
    """1,000 stored versions, one of them with 10,000 files (the target says "up to")."""
    store = stand_in.store
    with store.lock:
        for n in range(1000):
            revision = f"{n:040x}"
            count = 10_000 if n == 0 else 20
            version = Version("acme", f"m{n}", revision, state="complete")
            for i in range(count):
                path = f"part-{i:05d}.bin"
                version.files[path] = StoredFile(path, 10, f"{i:064x}", "virtual", "regular")
            store.versions[("acme", f"m{n}", revision)] = version
            store.repos.add(("acme", f"m{n}"))
    h = auth(stand_in)
    big = httpx.get(
        f"{stand_in.url}/artifactory/api/storage/models-hf/acme/m0/{0:040x}",
        params={"list": "", "deep": 1},
        headers=h,
    ).json()
    assert len(big["files"]) == 10_000
    small = httpx.get(
        f"{stand_in.url}/artifactory/api/storage/models-hf/acme/m999/{999:040x}",
        params={"list": "", "deep": 1},
        headers=h,
    ).json()
    assert len(small["files"]) == 20
    assert len(stand_in.repositories()) == 1000


# --- NFR7.2: eight uploads at once ----------------------------------------------------------------
def test_eight_concurrent_uploads_to_different_versions_do_not_mix(api, stand_in, tmp_path):
    api.create_repo("acme/many", exist_ok=True)

    def one(n: int):
        folder = tmp_path / f"f{n}"
        folder.mkdir()
        (folder / "config.json").write_bytes(f'{{"n": {n}}}'.encode())
        (folder / "weights.safetensors").write_bytes(bytes([n]) * 5000)
        return n, api.upload_folder(
            repo_id="acme/many", folder_path=str(folder), revision=f"{n:040x}"
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        done = list(pool.map(one, range(1, 9)))
    assert len(done) == 8
    for n in range(1, 9):
        files = {f.path: f for f in stand_in.version_files("acme/many", f"{n:040x}")}
        assert set(files) == {"config.json", "weights.safetensors"}
        assert files["weights.safetensors"].size == 5000
        assert files["config.json"].size == len(f'{{"n": {n}}}')
        assert stand_in.version_state("acme/many", f"{n:040x}") == "complete"


# --- NFR5.3: the token and the content never reach the record or the logs ------------------------
def test_the_token_and_the_content_are_in_no_record_and_no_log(api, stand_in, tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    folder = tmp_path / "m"
    folder.mkdir()
    (folder / "config.json").write_bytes(b'{"secret-content-marker": 1}')
    (folder / "w.safetensors").write_bytes(b"SECRETWEIGHTS" * 400)
    api.create_repo("acme/hush", exist_ok=True)
    api.upload_folder(repo_id="acme/hush", folder_path=str(folder), revision="b" * 40)
    seen = json.dumps(stand_in.calls) + " ".join(r.getMessage() for r in caplog.records)
    seen += " ".join(str(r.__dict__) for r in caplog.records)
    assert stand_in.token not in seen
    assert "secret-content-marker" not in seen and "SECRETWEIGHTS" not in seen


# --- NFR6.1: the shared log shape -----------------------------------------------------------------
def test_run_on_its_own_it_logs_json_lines_with_the_shared_fields(tmp_path):
    token = "json-log-token-91"
    proc = subprocess.Popen(
        [sys.executable, "-m", "modelhub_stand_in", "--token", token, "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        cwd=tmp_path,
    )
    try:
        first = proc.stdout.readline()
        url = first.split("listening on ")[1].split(" ")[0]
        httpx.get(
            f"{url}/artifactory/api/storage/models-hf", headers={"Authorization": f"Bearer {token}"}
        )
        time.sleep(0.3)
    finally:
        proc.terminate()
        out = proc.communicate(timeout=20)[0]
    lines = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
    requests = [x for x in lines if x.get("event") == "request"]
    assert requests, out
    entry = requests[0]
    assert {"ts", "level", "service", "event", "message"} <= set(entry)
    assert entry["service"] == "stand-in" and entry["status"] == 200
    assert token not in out


# --- NFR5.6: no credential from the environment -------------------------------------------------
def test_a_token_in_the_environment_is_never_used(monkeypatch, tmp_path):
    for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "ARTIFACTORY_TOKEN", "JFROG_ACCESS_TOKEN"):
        monkeypatch.setenv(name, "env-token-should-not-count")
    with StandIn(token="the-callers-token", workdir=tmp_path) as s:
        url = f"{s.url}/artifactory/api/storage/models-hf"
        assert (
            httpx.get(
                url, headers={"Authorization": "Bearer env-token-should-not-count"}
            ).status_code
            == 401
        )
        assert httpx.get(url, headers=auth(s)).status_code == 200
    for source in SRC.glob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert "os.environ" not in text and "getenv" not in text, source.name


# --- NFR8.1: nothing leaves the machine ---------------------------------------------------------
def test_with_other_sockets_blocked_a_full_round_trip_still_works(
    api, stand_in, tmp_path, monkeypatch
):
    real_connect = socket.socket.connect
    refused: list = []

    def guarded(self, address):
        host = address[0] if isinstance(address, tuple) else None
        if host is not None and not ipaddress.ip_address(socket.gethostbyname(host)).is_loopback:
            refused.append(address)
            raise OSError(f"blocked: {address}")
        return real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)
    folder = tmp_path / "m"
    folder.mkdir()
    (folder / "config.json").write_bytes(b"{}")
    (folder / "w.safetensors").write_bytes(b"W" * 4096)
    api.create_repo("acme/local", exist_ok=True)
    api.upload_folder(repo_id="acme/local", folder_path=str(folder), revision="c" * 40)
    assert stand_in.version_state("acme/local", "c" * 40) == "complete"
    assert stand_in.delete_version("acme/local", "c" * 40) == 204
    assert refused == []


_ = pytest
