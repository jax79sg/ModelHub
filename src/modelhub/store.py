"""The model store the web app reads (contract C3): layout, pointers and listing."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from modelhub import fsutil

_COMMIT = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class StorePaths:
    store: Path
    model_id: str

    @property
    def model_dir(self) -> Path:
        return Path(self.store, "models", *self.model_id.split("/"))

    @property
    def commits(self) -> Path:
        return self.model_dir / "commits"

    def commit_dir(self, commit: str) -> Path:
        return self.commits / commit

    def partial_dir(self, commit: str) -> Path:
        return self.commits / f".{commit}.partial"


def _captured_at(paths: StorePaths, commit: str) -> str:
    try:
        text = (paths.commit_dir(commit) / "manifest.json").read_text(encoding="utf-8")
        return str(json.loads(text).get("captured_at", ""))
    except (OSError, ValueError):
        return ""


def update_pointers(paths: StorePaths, commit: str, requested_revision: str) -> None:
    """Small text files, not links: links need special rights on Windows (CT-7).

    `latest` follows the most recently captured version, so unpacking an older bundle again
    never moves it backwards. Running this again with the same arguments changes nothing,
    which is what lets a stopped unpack be finished safely.
    """
    if requested_revision == "main":
        current = _read_pointer(paths.model_dir / "latest")
        if (
            current is None
            or current == commit
            or _captured_at(paths, current) <= _captured_at(paths, commit)
        ):
            fsutil.atomic_write_text(paths.model_dir / "latest", commit + "\n")
    if not _COMMIT.match(requested_revision):
        fsutil.atomic_write_text(paths.model_dir / "refs" / requested_revision, commit + "\n")


@dataclass
class ListedModel:
    model_id: str
    commit: str
    captured_at: str | None
    size: int | None
    license: str | None
    latest: bool


def list_models(store: Path) -> list[ListedModel]:
    """Every version of every model in the store, from each version's summary.json."""
    models_root = Path(store) / "models"
    found: list[ListedModel] = []
    if not models_root.is_dir():
        return found
    for commits_dir in _commit_folders(models_root):
        model_dir = commits_dir.parent
        model_id = model_dir.relative_to(models_root).as_posix()
        latest = _read_pointer(model_dir / "latest")
        with os.scandir(commits_dir) as entries:
            for entry in sorted(entries, key=lambda e: e.name):
                if entry.name.startswith(".") or not entry.is_dir():
                    continue
                found.append(_read_entry(Path(entry.path), model_id, entry.name, latest))
    return sorted(found, key=lambda m: (m.model_id, m.captured_at or "", m.commit))


def _commit_folders(root: Path):
    """Folders named `commits` anywhere under the models folder (ids have one or two parts)."""
    stack = [root]
    while stack:
        current = stack.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                if not entry.is_dir(follow_symlinks=False):
                    continue
                if entry.name == "commits":
                    yield Path(entry.path)
                elif not entry.name.startswith("."):
                    stack.append(Path(entry.path))


def _read_pointer(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _read_entry(folder: Path, model_id: str, commit: str, latest: str | None) -> ListedModel:
    try:
        summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        summary = {}
    size = summary.get("size_bytes")
    if size is None and summary.get("files"):
        size = sum(f.get("size", 0) for f in summary["files"])
    license_doc = summary.get("license") or {}
    return ListedModel(
        model_id=model_id,
        commit=commit,
        captured_at=summary.get("captured_at"),
        size=size,
        license=license_doc.get("name") if isinstance(license_doc, dict) else None,
        latest=(commit == latest),
    )
