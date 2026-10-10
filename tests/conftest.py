"""Shared test helpers: a fake Hugging Face server that serves models from memory."""

import hashlib
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

import pytest

from modelhub import fsutil
from modelhub.hubclient import ModelNotFound, TransientHubError

COMMIT = "a" * 40


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class FakeHub:
    """Stands in for the Hugging Face Hub. Records calls and can inject failures."""

    def __init__(self):
        self.models: dict[str, dict] = {}
        self.calls: list[tuple] = []
        self.failures: dict[str, list[Exception]] = {}  # file path -> errors to raise first
        self.corrupt: set[str] = set()  # file paths served with wrong bytes
        self.delay = 0.0  # seconds each download takes
        self.active = 0  # downloads running right now
        self.max_active = 0  # the most that ran at the same time
        self._lock = threading.Lock()

    def add_model(
        self,
        repo_id: str,
        files: dict[str, bytes],
        commit: str = COMMIT,
        license: str | None = "mit",
        gated=False,
        private: bool = False,
        lfs_over: int = 1000,
    ) -> None:
        tree = []
        for path, data in sorted(files.items()):
            entry = {
                "type": "file",
                "oid": git_blob_sha1(data),
                "size": len(data),
                "path": path,
                "lastCommit": {"id": commit, "title": "t", "date": "2026-01-01T00:00:00.000Z"},
            }
            if len(data) >= lfs_over:
                entry["lfs"] = {
                    "oid": hashlib.sha256(data).hexdigest(),
                    "size": len(data),
                    "pointerSize": 134,
                }
                entry["securityFileStatus"] = {"status": "safe"}
            tree.append(entry)
            if "/" in path:
                tree.append(
                    {"type": "directory", "oid": "d" * 40, "size": 0, "path": path.split("/")[0]}
                )
        card = {"tags": ["test"], "language": ["en"]}
        if license:
            card["license"] = license
        info = {
            "_id": "1",
            "id": repo_id,
            "modelId": repo_id,
            "author": repo_id.split("/")[0],
            "sha": commit,
            "private": private,
            "gated": gated,
            "disabled": False,
            "downloads": 1234,
            "likes": 56,
            "tags": ["test", "safetensors"],
            "pipeline_tag": "text-generation",
            "library_name": "transformers",
            "createdAt": "2025-01-01T00:00:00.000Z",
            "lastModified": "2026-01-01T00:00:00.000Z",
            "usedStorage": sum(len(d) for d in files.values()),
            "cardData": card,
            "safetensors": {"parameters": {"F32": 10}, "total": 10},
            "siblings": [{"rfilename": p} for p in sorted(files)],
        }
        self.models[repo_id] = {
            "info": info,
            "tree": tree,
            "files": files,
            "commits": [{"id": commit, "title": "t", "message": "m", "authors": [], "date": "d"}],
            "refs": {
                "branches": [{"name": "main", "ref": "refs/heads/main", "targetCommit": commit}],
                "tags": [],
                "converts": [],
            },
        }

    def _model(self, repo_id: str) -> dict:
        if repo_id not in self.models:
            raise ModelNotFound(repo_id)
        return self.models[repo_id]

    def model_info(self, repo_id, revision="main"):
        self.calls.append(("model_info", repo_id, revision))
        return self._model(repo_id)["info"]

    def tree(self, repo_id, revision):
        self.calls.append(("tree", repo_id, revision))
        return self._model(repo_id)["tree"]

    def commits(self, repo_id, revision):
        self.calls.append(("commits", repo_id, revision))
        return self._model(repo_id)["commits"]

    def refs(self, repo_id):
        self.calls.append(("refs", repo_id))
        return self._model(repo_id)["refs"]

    def download_file(self, repo_id, revision, path, dest: Path, progress_cb=None):
        with self._lock:
            self.calls.append(("download", repo_id, revision, path))
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            if self.delay:
                time.sleep(self.delay)
            with self._lock:
                pending = self.failures.get(path)
                error = pending.pop(0) if pending else None
            if error:
                raise error
            data = self._model(repo_id)["files"][path]
            if path in self.corrupt:
                data = b"X" + data[1:]
            # like the real client, a download appears at its final name only when complete
            fsutil.atomic_write_bytes(dest, data)
            if progress_cb:
                progress_cb(len(data))
        finally:
            with self._lock:
                self.active -= 1

    def read_file(self, repo_id, revision, path) -> bytes:
        self.calls.append(("read_file", repo_id, revision, path))
        return self._model(repo_id)["files"][path]

    def downloads(self) -> list[str]:
        return [c[3] for c in self.calls if c[0] == "download"]


TINY_FILES = {
    "README.md": b"---\nlicense: mit\n---\n# Tiny\nA tiny test model.\n",
    "config.json": b'{"model_type": "tiny"}\n',
    "tokenizer.json": b'{"version": "1.0"}\n',
    "model.safetensors": bytes(range(256)) * 80,  # 20,480 bytes
}


class _PictureHandler(BaseHTTPRequestHandler):
    routes: ClassVar[dict]  # each test's server gets its own, see picture_server
    hits: ClassVar[list]

    def do_GET(self):
        type(self).hits.append(self.path)
        status, body, delay = type(self).routes.get(self.path, (404, b"", 0))
        if delay:
            time.sleep(delay)
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def picture_server():
    """A local web server for README pictures: set `server.routes[path] = (status, body, delay)`."""
    handler = type("Handler", (_PictureHandler,), {"routes": {}, "hits": []})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.base = f"http://127.0.0.1:{server.server_address[1]}"
    server.routes = handler.routes
    server.hits = handler.hits
    yield server
    server.shutdown()
    server.server_close()


@pytest.fixture
def fake_hub():
    hub = FakeHub()
    hub.add_model("org/tiny", dict(TINY_FILES))
    return hub


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A private MODELHUB_HOME so tests never touch real keys."""
    path = tmp_path / "home"
    monkeypatch.setenv("MODELHUB_HOME", str(path))
    return path


@pytest.fixture
def key_id(home):
    from modelhub import signing

    return signing.create_key("test")["key_id"]


@pytest.fixture
def pulled(fake_hub, tmp_path):
    """A finished download record for org/tiny."""
    from modelhub import pull

    return pull.pull_model(fake_hub, "org/tiny", tmp_path / "work", selection={"all"}).record_dir


@pytest.fixture
def bundle_dir(pulled, key_id, tmp_path):
    """A signed bundle in 4 KB pieces whose key this computer already trusts."""
    from modelhub import bundle, signing

    out = tmp_path / "bundle"
    bundle.bundle_record(pulled, out, key_id, piece_size=4096)
    doc = signing.export_public(key_id, tmp_path / "pub.json")
    signing.trust_key(doc, doc["fingerprint"])
    return out


@pytest.fixture
def no_network(monkeypatch):
    """Any attempt to open a network connection fails the test (NFR5.1)."""
    import socket

    def refuse(*args, **kwargs):
        raise AssertionError("a network connection was attempted")

    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.fixture
def transient():
    return TransientHubError("simulated network error")
