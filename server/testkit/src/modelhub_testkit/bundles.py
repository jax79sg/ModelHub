"""Make a real signed bundle for tests (the same code the CLI uses to make one).

A small in-memory stand-in for the Hugging Face Hub feeds ``pull_model``; ``bundle_record`` then
slices and signs it. The signing key lives in a private home folder, so nothing touches the real
keys of whoever runs the tests.
"""

from __future__ import annotations

import hashlib
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from modelhub import bundle, fsutil, pull, signing

COMMIT = "a" * 40
DEFAULT_FILES = {
    "README.md": b"---\nlicense: mit\n---\n# Tiny\nA tiny quantized test model.\n",
    "config.json": b'{"model_type": "tiny"}\n',
    "tokenizer.json": b'{"version": "1.0"}\n',
    "model.safetensors": bytes(range(256)) * 80,  # 20,480 bytes
}


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


class MiniHub:
    """What ``pull_model`` needs from the Hugging Face client, served from memory."""

    def __init__(self, repo_id: str, files: dict[str, bytes], commit: str) -> None:
        self.repo_id, self.files, self.commit = repo_id, files, commit

    def model_info(self, repo_id, revision="main"):
        return {
            "_id": "1",
            "id": repo_id,
            "modelId": repo_id,
            "sha": self.commit,
            "private": False,
            "gated": False,
            "disabled": False,
            "downloads": 1234,
            "likes": 56,
            "tags": ["test", "safetensors"],
            "pipeline_tag": "text-generation",
            "library_name": "transformers",
            "createdAt": "2025-01-01T00:00:00.000Z",
            "lastModified": "2026-01-01T00:00:00.000Z",
            "usedStorage": sum(len(d) for d in self.files.values()),
            "cardData": {"tags": ["test"], "language": ["en"], "license": "mit"},
            "safetensors": {"parameters": {"F32": 10}, "total": 10},
            "siblings": [{"rfilename": p} for p in sorted(self.files)],
        }

    def tree(self, repo_id, revision):
        out = []
        for path, data in sorted(self.files.items()):
            entry = {"type": "file", "oid": _git_blob_sha1(data), "size": len(data), "path": path}
            entry["securityFileStatus"] = {"status": "safe"}
            out.append(entry)
        return out

    def commits(self, repo_id, revision):
        return [{"id": self.commit, "title": "t", "message": "m", "authors": [], "date": "d"}]

    def refs(self, repo_id):
        return {
            "branches": [{"name": "main", "ref": "refs/heads/main", "targetCommit": self.commit}],
            "tags": [],
            "converts": [],
        }

    def download_file(self, repo_id, revision, path, dest: Path, progress_cb=None):
        fsutil.atomic_write_bytes(dest, self.files[path])
        if progress_cb:
            progress_cb(len(self.files[path]))

    def read_file(self, repo_id, revision, path) -> bytes:
        return self.files[path]


@dataclass
class MadeBundle:
    directory: Path
    model_id: str
    commit: str
    stem: str
    public_key: dict  # the signer's public key document (what a service would trust)
    files: dict[str, bytes] = field(default_factory=dict)

    @property
    def description_path(self) -> Path:
        return self.directory / f"{self.stem}.bundle.json"

    @property
    def signature_path(self) -> Path:
        return self.directory / f"{self.stem}.bundle.sig"

    def pieces(self) -> list[Path]:
        return sorted(p for p in self.directory.glob("*.part-*") if not p.name.startswith("."))


@contextmanager
def _home(path: Path):
    old = os.environ.get("MODELHUB_HOME")
    os.environ["MODELHUB_HOME"] = str(path)
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("MODELHUB_HOME", None)
        else:
            os.environ["MODELHUB_HOME"] = old


def make_bundle(
    work: Path,
    model_id: str = "org/tiny",
    files: dict[str, bytes] | None = None,
    commit: str = COMMIT,
    piece_size: int = 4096,
) -> MadeBundle:
    """A signed bundle of ``model_id`` in pieces of about ``piece_size`` bytes."""
    work = Path(work)
    files = dict(files or DEFAULT_FILES)
    with _home(work / "home"):
        key = signing.create_key("test")
        record_dir = pull.pull_model(
            MiniHub(model_id, files, commit), model_id, work / "pull", selection={"all"}
        ).record_dir
        out = work / "bundle"
        bundle.bundle_record(record_dir, out, key["key_id"], piece_size=piece_size)
        exported = signing.export_public(key["key_id"], work / "public.json")
        public = signing.read_public_doc(Path(work / "public.json")) if exported else {}
    from modelhub.pieces import stem_for

    return MadeBundle(out, model_id, commit, stem_for(model_id, commit), public, files)
