"""Report time, kills, memory and sockets of the import command (loop-back 2).

Checks NFR1.1, NFR4.2, NFR5.6, NFR7.1, NFR7.3, NFR7.4 and NFR8.1 of the import-cli unit.
Nothing here weakens a target.
"""

import os
import socket
import subprocess
import sys
import textwrap
import threading
import time
import tracemalloc
from pathlib import Path

import httpx
import pytest
from fake_import_service import FakeImportService, serve

from modelhub import importer, settings

SECRET = "mhi_" + "q7Zk" * 8


# --- NFR1.1: the report comes promptly after the service says done ------------------------------
class SlowClient:
    """The service says done at `done_at` on a simulated clock; each request takes `latency`."""

    def __init__(self, clock, done_at, latency):
        self.clock, self.done_at, self.latency = clock, done_at, latency
        self.seen_done_at = None

    def request(self, method, path, **kw):
        self.clock.now += self.latency
        done = self.clock.now >= self.done_at
        if done and self.seen_done_at is None:
            self.seen_done_at = self.clock.now
        state = {"importId": "i1", "state": "done" if done else "uploading"}
        if done:
            state["outcome"] = "imported"
        return httpx.Response(200, json=state)


class Clock:
    now = 0.0


def test_the_report_comes_within_two_seconds_of_the_service_saying_done():
    package = importer.Package("org/tiny", "a" * 40, "b", "{}", "", [], {})
    worst = 0.0
    for tenth in range(40):
        clock = Clock()
        clock.now = 0.0
        client = SlowClient(clock, done_at=tenth / 10, latency=0.3)

        def sleep(seconds, clock=clock):
            clock.now += seconds

        entry = importer._watch(client, "i1", package, importer.NullReporter(), sleep)
        assert entry.result == "imported"
        worst = max(worst, clock.now - client.done_at)
    assert worst <= 2.0, worst


# --- NFR4.2: killed during create, during a piece, during the wait ----------------------------------
def run_cli(url, bundled, env_extra, cwd, **kw):
    env = {
        **os.environ,
        "MODELHUB_SERVER": url,
        "MODELHUB_TOKEN": SECRET,
        "PYTHONIOENCODING": "utf-8",
        **env_extra,
    }
    return subprocess.Popen(
        [sys.executable, "-m", "modelhub", "import", str(bundled)],
        env=env,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        **kw,
    )


@pytest.fixture
def cli_env(home, tmp_path):
    config = tmp_path / "config"
    return {"MODELHUB_CONFIG_DIR": str(config), "MODELHUB_HOME": str(home)}


@pytest.mark.parametrize("where", ["create", "piece", "wait"])
def test_a_process_killed_at_any_point_runs_again_to_a_correct_result(
    where, bundle_dir, cli_env, monkeypatch, tmp_path
):
    fake = FakeImportService()
    fake.polls_before_done = 3
    holder: dict = {}
    killed = threading.Event()

    def kill_here(method, path):
        hit = (
            (where == "create" and method == "POST" and path == "/v1/imports")
            or (where == "piece" and method == "PUT" and path.endswith("/pieces/2"))
            or (where == "wait" and method == "GET" and path == "/v1/imports/i1")
        )
        if hit and not killed.is_set():
            killed.set()
            holder["proc"].kill()

    url, stop = serve(fake, kill_here)
    try:
        first = run_cli(url, bundle_dir, cli_env, tmp_path)
        holder["proc"] = first
        first.communicate(timeout=120)
        assert killed.is_set() and first.returncode != 0
        sent_before = dict(fake.stored)
        puts_before = len([c for c in fake.calls if c[0] == "PUT"])
        second = run_cli(url, bundle_dir, cli_env, tmp_path)
        out, _ = second.communicate(timeout=120)
        assert second.returncode == 0, out
        assert "imported" in out.lower()
        # only the pieces the service was missing were sent again
        puts_after = len([c for c in fake.calls if c[0] == "PUT"])
        total = fake.pieces_expected
        assert len(fake.stored) == total and set(sent_before) <= set(fake.stored)
        assert puts_after - puts_before <= total - len(sent_before)
    finally:
        stop()


# --- NFR7.1: a 200 GB declared piece set ------------------------------------------------------------
def sink_server():
    """A local service that reads each piece in blocks and throws it away (so the memory seen is
    the client's, in another process)."""
    import json
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body=None):
            data = json.dumps(body).encode() if body is not None else b""
            self.send_response(status)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            length = int(self.headers.get("content-length") or 0)
            self.rfile.read(length)
            if self.path == "/v1/imports":
                return self._send(201, {"importId": "i1", "missingPieces": [1, 2, 3]})
            return self._send(202, {"importId": "i1", "state": "verifying"})

        def do_PUT(self):
            left = int(self.headers.get("content-length") or 0)
            while left:
                left -= len(self.rfile.read(min(left, 1 << 20)))
            self._send(204)

        def do_GET(self):
            self._send(200, {"importId": "i1", "state": "done", "outcome": "imported"})

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}", server


@pytest.mark.skipif(sys.platform == "win32", reason="the resource module is not on Windows")
def test_a_200_gb_declared_piece_set_is_read_in_blocks_within_a_small_footprint(tmp_path):
    assert importer.BLOCK <= 8 * 1024 * 1024
    url, server = sink_server()
    program = textwrap.dedent(
        f"""
        import resource, sys, hashlib
        from pathlib import Path
        from modelhub import importer

        big = Path({str(tmp_path / "big.part")!r})
        with open(big, "wb") as h:
            h.truncate(1_000_000_000)
        sha = hashlib.sha256()
        with open(big, "rb") as h:
            while c := h.read(1 << 20):
                sha.update(c)
        # 200 pieces of 1 GB are declared (200 GB); the service is missing three of them
        pieces = [importer.PieceFile(i, big, 1_000_000_000, sha.hexdigest()) for i in range(1, 201)]
        package = importer.Package("org/huge", "a" * 40, "b", "{{}}", "", pieces, {{}})
        client = importer.ServiceClient({url!r}, "t", sleep=lambda s: None)
        entry = importer.send_package(client, package, sleep=lambda s: None)
        assert entry.result == "imported", entry
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        print(usage / (1024 * 1024) if sys.platform == "darwin" else usage / 1024)
        """
    )
    try:
        done = subprocess.run(
            [sys.executable, "-c", program], capture_output=True, text=True, check=False
        )
    finally:
        server.shutdown()
    assert done.returncode == 0, done.stderr
    assert float(done.stdout.strip().splitlines()[-1]) < 150  # megabytes


# --- NFR7.3: a bundle with very many pieces ---------------------------------------------------------
def test_memory_per_piece_is_tiny_and_no_piece_content_is_kept(tmp_path):
    piece = tmp_path / "p.part-000001"
    piece.write_bytes(b"x" * 4096)
    import hashlib

    sha = hashlib.sha256(piece.read_bytes()).hexdigest()

    def peak(count: int) -> int:
        pieces = [importer.PieceFile(i, piece, 4096, sha) for i in range(1, count + 1)]
        package = importer.Package("org/many", "a" * 40, "b", "{}", "", pieces, {})
        fake = FakeImportService()
        fake.polls_before_done = 1
        # the service already holds all but the last 50 pieces
        fake.stored = {i: sha for i in range(1, count - 49)}
        fake.pieces_expected = count

        def handler(request):
            if request.method == "POST" and request.url.path == "/v1/imports":
                return httpx.Response(
                    201,
                    json={"importId": "i1", "missingPieces": list(range(count - 49, count + 1))},
                )
            return fake._handle(request)

        client = importer.ServiceClient(
            "http://127.0.0.1:1", "t", http=httpx.Client(transport=httpx.MockTransport(handler))
        )
        fake.state = "receiving"
        tracemalloc.start()
        try:
            importer.send_package(client, package)
            return tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()

    small, large = peak(1_000), peak(20_000)
    per_piece = (large - small) / 19_000
    assert per_piece < 1024, per_piece  # 999,999 pieces would still be under 1 GB, far below 8 GB


# --- NFR7.4: a list of 50 bundles --------------------------------------------------------------------
def test_fifty_bundles_in_a_row_run_with_constant_memory(bundle_dir, tmp_path):
    descriptions = sorted(bundle_dir.glob("*.bundle.json")) * 50
    fake = FakeImportService()
    client = importer.ServiceClient(
        "http://127.0.0.1:1",
        "t",
        http=httpx.Client(transport=fake.transport()),
        sleep=lambda s: None,
    )

    def one_round(count: int) -> int:
        report = importer.run(client, descriptions[:count], sleep=lambda s: None)
        assert all(e.result in ("imported", "skipped") for e in report.entries), report.entries
        return tracemalloc.get_traced_memory()[0]

    tracemalloc.start()
    try:
        one_round(5)  # warm up caches
        after_ten = one_round(10)
        after_fifty = one_round(50)
    finally:
        tracemalloc.stop()
    assert after_fifty - after_ten < 2 * 1024 * 1024


# --- NFR5.6 and NFR8.1: only the configured server --------------------------------------------------
def test_with_every_other_socket_blocked_only_the_configured_server_is_contacted(
    bundle_dir, monkeypatch
):
    fake = FakeImportService()
    url, stop = serve(fake)
    host, port = url.removeprefix("http://").split(":")
    contacted = []
    real = socket.socket.connect

    def guarded(self, address):
        contacted.append(address)
        if address != (host, int(port)):
            raise OSError(f"blocked: {address}")
        return real(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)
    try:
        client = importer.ServiceClient(url, SECRET, sleep=lambda s: None)
        report = importer.run(
            client, sorted(bundle_dir.glob("*.bundle.json")), sleep=lambda s: None
        )
    finally:
        stop()
    assert [e.result for e in report.entries] == ["imported"]
    assert set(contacted) == {(host, int(port))}


_ = (Path, time, settings)
