"""Put versions into the real Catalog the way the import service does (contract C2)."""

import json

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082"
)


def put(catalog_http, issuer, model_id, commit, files=None, documents=None, **version):
    base = {
        "model_id": model_id,
        "commit": commit,
        "captured_at": "2026-01-02T03:04:05Z",
        "license": "mit",
        "language": ["en"],
        "tags": ["a"],
        "task": "text-generation",
        "library": "transformers",
        "downloads": 1234,
        "likes": 5,
        "parameter_count": 500_000_000,
        "size_bytes": 100,
        "counts_captured_at": "2026-01-02T03:04:05Z",
        "created_at": "2025-01-01T00:00:00Z",
        "last_modified_at": "2025-06-01T00:00:00Z",
        "refs": [{"name": "main", "kind": "branch", "commit": commit}],
        "files": files
        if files is not None
        else [
            {
                "path": "config.json",
                "size_bytes": 23,
                "sha256": "a" * 64,
                "downloaded": True,
                "safety_scan": "safe",
            },
            {"path": "big.bin", "size_bytes": 999, "sha256": "b" * 64, "downloaded": False},
        ],
    }
    base.update(version)
    record = {
        "version": base,
        "importRecord": {
            "importedBy": {"id": "u1", "name": "ada"},
            "importedAt": "2026-02-01T00:00:00Z",
            "computer": "pc",
            "bundleName": "b",
            "bundleSha256": "c" * 64,
            "signingKeyFingerprint": "aaaa-bbbb",
            "toolVersion": "1",
            "checkResults": {"ok": True},
            "outcome": "imported",
        },
    }
    docs = (
        documents
        if documents is not None
        else [("readme/README.md", b"# Hello\n\nA *tiny* model.\n", "text/markdown")]
    )
    r = catalog_http.put(
        f"/v1/models/{model_id}/versions/{commit}",
        data={"record": json.dumps(record)},
        files=[("documents", (n, d, c)) for n, d, c in docs] or None,
        headers={"Authorization": f"Bearer {issuer.service_token()}"},
    )
    assert r.status_code in (200, 201), r.text
