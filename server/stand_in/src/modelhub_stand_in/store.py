"""What the stand-in remembers: repositories, versions, files (entities of the functional design)."""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from .rules import commit_hash, is_commit_hash

LAYOUTS = ("flat", "nested")
# Files this big, or with these endings, go through the large-file (Git LFS) route.
LFS_MIN_BYTES = 10 * 1024 * 1024
LFS_SUFFIXES = (".safetensors", ".bin", ".gguf", ".pt", ".pth", ".onnx", ".h5", ".msgpack", ".ot")


@dataclass
class StoredFile:
    path: str
    size: int
    sha256: str
    mode: str  # "kept" (content held) or "virtual" (name, size and checksum only)
    transfer: str  # "regular" or "large-file"
    data: Path | None = None


@dataclass
class Version:
    organisation: str
    model: str
    revision: str
    state: str = "partial"
    files: dict[str, StoredFile] = field(default_factory=dict)
    committed_at: float | None = None


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Store:
    def __init__(self, workdir: Path, keep_limit_bytes: int, layout: str) -> None:
        self.workdir = workdir
        self.content = workdir / "content"
        self.content.mkdir(parents=True, exist_ok=True)
        self.keep_limit = keep_limit_bytes
        self.layout = layout
        self.keep_paths: set[str] = set()
        self.write_allowed = True
        self.overwrite_allowed = False
        self.lock = threading.RLock()
        self.repos: set[tuple[str, str]] = set()
        self.versions: dict[tuple[str, str, str], Version] = {}
        self.aliases: dict[tuple[str, str, str], str] = {}
        # large objects uploaded and waiting for a commit to name them: oid -> (size, path or None)
        self.objects: dict[str, tuple[int, Path | None]] = {}

    # --- names -------------------------------------------------------------------------------
    def resolve(self, org: str, model: str, revision: str) -> str:
        if is_commit_hash(revision):
            return revision.lower() if (org, model, revision.lower()) in self.versions else revision
        return self.aliases.get((org, model, revision), revision)

    def get(self, org: str, model: str, revision: str, complete_only: bool = True):
        real = self.resolve(org, model, revision)
        version = self.versions.get((org, model, real))
        if version is None or (complete_only and version.state != "complete"):
            return None
        return version

    # --- content -----------------------------------------------------------------------------
    def keeps(self, size: int, path: str | None) -> bool:
        return size <= self.keep_limit or (path is not None and path in self.keep_paths)

    def keep_bytes(self, data: bytes) -> Path:
        digest = sha256_hex(data)
        target = self.content / digest
        if not target.exists():
            target.write_bytes(data)
        return target

    def upload_mode(self, path: str, size: int) -> str:
        if size >= LFS_MIN_BYTES or path.lower().endswith(LFS_SUFFIXES):
            return "lfs"
        return "regular"

    # --- layout ------------------------------------------------------------------------------
    def version_dir(self, org: str, model: str, revision: str) -> str:
        if self.layout == "nested":
            return f"{org}/{model}/revisions/{revision}"
        return f"{org}/{model}/{revision}"

    def file_uri(self, version: Version, path: str) -> str:
        base = self.version_dir(version.organisation, version.model, version.revision)
        if self.layout == "nested":
            return f"/{base}/files/{path}"
        return f"/{base}/{path}"

    # --- commit ------------------------------------------------------------------------------
    def final_revision(self, given: str, files: list[StoredFile]) -> str:
        if is_commit_hash(given):
            return given.lower()
        return commit_hash([(f.path, f.sha256) for f in files])

    def now(self) -> float:
        return time.time()
