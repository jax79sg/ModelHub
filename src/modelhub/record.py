"""The download record (contract C1): the folder `pull` writes and `bundle` packs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from modelhub import __version__
from modelhub.fsutil import atomic_write_text, sha256_file

FORMAT_VERSION = "1.0"
SUPPORTED_MAJOR = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class UnsupportedFormat(Exception):
    """A file written by a newer, incompatible version of the tool."""


def check_format_version(value: str) -> None:
    """A newer tool reads anything with the same or an earlier major version (Q3 A)."""
    try:
        major = int(str(value).split(".")[0])
    except ValueError as error:
        raise UnsupportedFormat(f"unreadable format version: {value!r}") from error
    if major > SUPPORTED_MAJOR:
        raise UnsupportedFormat(
            f"format version {value} is newer than this tool understands "
            f"(it reads up to major version {SUPPORTED_MAJOR})"
        )


@dataclass(frozen=True)
class RecordPaths:
    work: Path
    model_id: str
    commit: str

    @property
    def root(self) -> Path:
        return Path(self.work, "models", *self.model_id.split("/"), "commits", self.commit)

    @property
    def files(self) -> Path:
        return self.root / "files"

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def readme(self) -> Path:
        return self.root / "readme"

    @property
    def manifest(self) -> Path:
        return self.root / "manifest.json"

    @property
    def summary(self) -> Path:
        return self.root / "summary.json"


def build_file_entries(files_dir: Path, hub_info: dict[str, dict]) -> list[dict]:
    """One manifest row per file under `files_dir`, hashed in blocks (FR6.1, FR5.4)."""
    entries = []
    for path in sorted(p for p in Path(files_dir).rglob("*") if p.is_file()):
        rel = path.relative_to(files_dir).as_posix()
        hub = hub_info.get(rel, {})
        lfs = hub.get("lfs") or {}
        entries.append(
            {
                "path": rel,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
                "hub_sha256": lfs.get("oid"),
                "hub_oid": hub.get("oid"),
                "scan": hub.get("securityFileStatus"),
            }
        )
    return entries


def new_manifest(
    model_id: str,
    commit: str,
    requested_revision: str,
    files: list[dict],
    captured_at: str,
    tool_version: str = __version__,
) -> dict:
    return {
        "format_version": FORMAT_VERSION,
        "tool_version": tool_version,
        "captured_at": captured_at,
        "model_id": model_id,
        "commit": commit,
        "requested_revision": requested_revision,
        "files": files,
    }


def write_manifest(paths: RecordPaths, manifest: dict) -> None:
    atomic_write_text(paths.manifest, json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def load_manifest(path: Path) -> dict:
    # utf-8-sig: a file saved by Windows Notepad may start with a byte-order mark
    manifest = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    check_format_version(manifest.get("format_version", "0"))
    return manifest
