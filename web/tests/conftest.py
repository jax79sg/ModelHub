import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hubsite.app import create_app

COMMIT = "a" * 40
OLD = "b" * 40


def make_model(
    store: Path,
    model_id: str,
    *,
    pipeline="text-generation",
    library="transformers",
    license="mit",
    downloads=100,
    likes=5,
    params=1_000_000,
    readme="# Title\n\nHello **world**.\n",
    refs=("main",),
    language=None,
    commit=COMMIT,
    extra_files=None,
):
    root = store / "models" / model_id
    cdir = root / "commits" / commit
    (cdir / "files").mkdir(parents=True)
    (cdir / "raw").mkdir()
    (cdir / "readme").mkdir()
    files = {"config.json": '{"a": 1}\n', "weights.bin": b"\x00\x01\x02binary", **(extra_files or {})}
    summary_files = []
    for rel, data in files.items():
        p = cdir / "files" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data if isinstance(data, bytes) else data.encode())
        summary_files.append({"path": rel, "size": p.stat().st_size, "sha256": "0" * 64, "type": "settings", "scan": {"status": "safe"}})
    # modelhub's own download cache must never be shown
    cache = cdir / "files" / ".modelhub-dl" / ".cache"
    cache.mkdir(parents=True)
    (cache / "x.lock").write_text("")
    summary_files.append({"path": ".modelhub-dl/.cache/x.lock", "size": 0, "sha256": "1" * 64, "type": "settings", "scan": None})
    readme_info = {"original": None, "local": None, "pictures": []}
    if readme is not None:
        (cdir / "files" / "README.md").write_text(readme)
        (cdir / "readme" / "README.local.md").write_text(readme)
        readme_info = {"original": "files/README.md", "local": "readme/README.local.md", "pictures": []}
    summary = {
        "format_version": "1.0",
        "tool_version": "1.1.1",
        "model_id": model_id,
        "commit": commit,
        "captured_at": "2026-10-11T14:33:02Z",
        "card": {
            "license": license,
            "language": language,
            "tags": ["pytorch", "dataset:x/y", "arxiv:1234.5678", "region:us"],
            "pipeline_tag": pipeline,
            "library_name": library,
        },
        "stats": {
            "downloads": downloads,
            "likes": likes,
            "used_storage_bytes": 10,
            "parameter_counts": {"parameters": {"F32": params}, "total": params} if params else None,
        },
        "created_at": "2022-01-01T00:00:00.000Z",
        "last_modified": "2025-01-01T00:00:00.000Z",
        "license": {"name": license, "file": None, "text_available": False},
        "readme": readme_info,
        "files": summary_files,
        "history": {},
    }
    (cdir / "summary.json").write_text(json.dumps(summary))
    tree = [
        {
            "type": "file",
            "oid": "1",
            "size": f["size"],
            "path": f["path"],
            "lastCommit": {"id": commit, "title": "init", "date": "2024-01-01T00:00:00.000Z"},
        }
        for f in summary_files
        if not f["path"].startswith(".modelhub-dl")
    ]
    tree.append({"type": "file", "oid": "2", "size": 999, "path": "missing.safetensors", "lastCommit": None})
    tree.append({"type": "directory", "oid": "3", "size": 0, "path": "sub", "lastCommit": None})
    tree.append({"type": "file", "oid": "4", "size": 5, "path": "sub/inner.txt", "lastCommit": None})
    (cdir / "raw" / "tree.json").write_text(json.dumps(tree))
    (cdir / "raw" / "commits.json").write_text(
        json.dumps(
            [
                {"id": commit, "title": "Second", "message": "", "authors": [{"user": "alice"}], "date": "2025-01-01T00:00:00.000Z"},
                {"id": OLD, "title": "First", "message": "", "authors": [{"user": "bob"}], "date": "2024-01-01T00:00:00.000Z"},
            ]
        )
    )
    (cdir / "raw" / "refs.json").write_text(json.dumps({"tags": [], "branches": [{"name": "main", "targetCommit": commit}]}))
    (root / "latest").write_text(commit)
    for r in refs:
        (root / "refs").mkdir(exist_ok=True)
        (root / "refs" / r).write_text(commit)
    return root


@pytest.fixture
def store(tmp_path):
    s = tmp_path / "store"
    make_model(s, "acme/alpha", downloads=1000, likes=10, params=5_000_000)
    make_model(
        s,
        "acme/beta",
        pipeline="fill-mask",
        library="pytorch",
        license="apache-2.0",
        downloads=50,
        likes=99,
        params=20_000_000_000,
        language="en",
    )
    make_model(s, "zed/gamma", pipeline=None, library=None, license=None, downloads=None, likes=None, params=None, readme=None)
    return s


@pytest.fixture
def client(store):
    return TestClient(create_app(store), headers={"accept": "text/html"})
