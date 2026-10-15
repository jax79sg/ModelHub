import copy
from datetime import datetime, timezone

import pytest
from modelhub_catalog import db
from modelhub_catalog.store import CatalogStore, Document

C1 = "1" * 40
C2 = "2" * 40
C3 = "3" * 40
PEPPER = b"test-pepper-" + b"p" * 20


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, **kw):
        from datetime import timedelta

        self.now += timedelta(**kw)


def make_record(model="acme/tiny", commit=C1, **over):
    version = {
        "model_id": model,
        "commit": commit,
        "captured_at": "2026-01-02T03:04:05Z",
        "license": "apache-2.0",
        "language": ["en"],
        "tags": ["text-generation", "llama"],
        "task": "text-generation",
        "library": "transformers",
        "parameter_count": 1_100_000_000,
        "downloads": 1000,
        "likes": 10,
        "size_bytes": 2_200_000_000,
        "counts_captured_at": "2026-01-02T03:04:05Z",
        "created_at": "2025-06-01T00:00:00Z",
        "last_modified_at": "2025-12-01T00:00:00Z",
        "refs": [{"name": "main", "kind": "branch", "commit": commit}],
        "files": [
            {
                "path": "config.json",
                "size_bytes": 10,
                "sha256": "a" * 64,
                "file_type": "json",
                "safety_scan": "safe",
                "downloaded": True,
            },
            {
                "path": "model.safetensors",
                "size_bytes": 2_200_000_000,
                "sha256": None,
                "file_type": "safetensors",
                "safety_scan": None,
                "downloaded": False,
            },
        ],
    }
    imp = {
        "importedBy": {"id": "u1", "name": "ada"},
        "importedAt": "2026-02-01T00:00:00Z",
        "computer": "pc1",
        "bundleName": "bundle-1",
        "bundleSha256": "c" * 64,
        "signingKeyFingerprint": "aaaa-bbbb-cccc-dddd",
        "toolVersion": "1.2.0",
        "checkResults": {"ok": True},
        "outcome": "imported",
    }
    version.update(over.pop("version", {}))
    imp.update(over.pop("importRecord", {}))
    record = {"version": version, "importRecord": imp}
    record.update(over)
    return record


def readme(text="# Tiny\nA small quantized model for tests.\n"):
    return Document("readme", "README.md", "text/markdown", text.encode())


def make_docs(*extra):
    return [readme(), Document("response", "model.json", "application/json", b'{"a": 1}'), *extra]


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def store(fresh_database, clock):
    db.migrate(fresh_database)
    s = CatalogStore(fresh_database, pepper=PEPPER, clock=clock)
    yield s
    s.close()


@pytest.fixture
def put(store):
    """Store a version with sensible defaults; returns the result."""

    def go(model="acme/tiny", commit=C1, docs=None, **over):
        record = make_record(model, commit, **over)
        return store.put_version(model, commit, copy.deepcopy(record), docs or make_docs())

    return go
