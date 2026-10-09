"""Manifest of a pulled repo: what was fetched, at which commit, with which hashes."""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from modelhub import __version__

MANIFEST_NAME = "manifest.json"
SNAPSHOT_DIR = "snapshot"  # repo files, exactly as on the Hub
METADATA_DIR = "metadata"  # Hub API responses (model_info.json, ...)
_SKIP_PARTS = {".cache"}  # huggingface_hub bookkeeping inside local_dir


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


@dataclass
class Manifest:
    repo_id: str
    repo_type: str
    revision: str  # resolved commit sha
    requested_revision: str
    files: dict[str, dict] = field(default_factory=dict)  # relpath -> {size, sha256}
    created_at: str = ""
    tool_version: str = __version__

    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=2, sort_keys=True)

    @classmethod
    def load(cls, root: Path) -> "Manifest":
        return cls(**json.loads((root / MANIFEST_NAME).read_text()))


def iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and rel.as_posix() != MANIFEST_NAME and not (set(rel.parts) & _SKIP_PARTS):
            yield rel


def build_manifest(root: Path, repo_id: str, repo_type: str, revision: str, requested: str) -> Manifest:
    m = Manifest(
        repo_id=repo_id,
        repo_type=repo_type,
        revision=revision,
        requested_revision=requested,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    for rel in iter_files(root):
        p = root / rel
        m.files[rel.as_posix()] = {"size": p.stat().st_size, "sha256": sha256_file(p)}
    return m


def verify_dir(root: Path) -> list[str]:
    """Return a list of problems (empty == OK)."""
    m = Manifest.load(root)
    problems = []
    for rel, info in m.files.items():
        p = root / rel
        if not p.is_file():
            problems.append(f"missing: {rel}")
        elif p.stat().st_size != info["size"]:
            problems.append(f"size mismatch: {rel}")
        elif sha256_file(p) != info["sha256"]:
            problems.append(f"hash mismatch: {rel}")
    extra = {r.as_posix() for r in iter_files(root)} - set(m.files)
    problems += [f"unlisted file: {r}" for r in sorted(extra)]
    return problems
