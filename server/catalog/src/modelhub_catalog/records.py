"""A version record as the import service sends it: checks and the stored checksum.

Rules BR1.2 (the checksum of the record and its documents), BR1.3 (a value not given is null,
never 0 or empty text), BR1.4 (what makes a record invalid), BR1.19 (unknown fields are ignored),
NFR5.6 and NFR7.5 (limits).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

RECORD_FORMAT = 1
MAX_DOCUMENT_BYTES = 16 * 1024 * 1024
MAX_DOCUMENTS = 1000
MAX_DOCUMENT_TOTAL_BYTES = 64 * 1024 * 1024
MAX_FILES = 10_000
DOCUMENT_KINDS = (
    "readme",
    "readme_local",
    "picture",
    "response",
    "manifest",
    "bundle_description",
    "bundle_signature",
    "licence",
)
OUTCOMES = ("imported", "repaired", "skipped")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class InvalidRecord(Exception):
    def __init__(self, field_name: str, message: str) -> None:
        super().__init__(f"{field_name}: {message}")
        self.field = field_name
        self.message = message


@dataclass
class Document:
    kind: str
    name: str
    content_type: str
    content: bytes
    picture_status: str | None = None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


@dataclass
class Validated:
    model_id: str
    commit: str
    version: dict
    files: list[dict]
    refs: list[dict]
    documents: list[Document]
    import_record: dict
    has_readme: bool
    card_text: str | None
    declared_checksums: dict = field(default_factory=dict)


def parse_time(value, name: str, required: bool = False) -> datetime | None:
    if value in (None, ""):
        if required:
            raise InvalidRecord(name, "a UTC time is required")
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            raise InvalidRecord(name, "not a time") from None
    if parsed.tzinfo is None:
        raise InvalidRecord(name, "the time must be in UTC (end with Z or give an offset)")
    return parsed.astimezone(timezone.utc)


def _count(value, name: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise InvalidRecord(name, "not a number")
    if value != int(value) or value < 0:
        raise InvalidRecord(name, "must be a whole number, not negative")
    return int(value)


def _text(value) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _text_list(value, name: str) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return [value] if value else None
    if not isinstance(value, list):
        raise InvalidRecord(name, "must be a list of text")
    return [str(x) for x in value]


def _safe_path(path: str) -> bool:
    if not path or path.startswith("/") or "\\" in path or re.match(r"^[A-Za-z]:", path):
        return False
    return all(part not in ("", ".", "..") for part in path.split("/"))


def _files(raw) -> list[dict]:
    if not isinstance(raw, list):
        raise InvalidRecord("files", "must be a list")
    if len(raw) > MAX_FILES:
        raise InvalidRecord("files", f"at most {MAX_FILES} files per version")
    seen: set[str] = set()
    out = []
    for entry in raw:
        path = entry.get("path", "") if isinstance(entry, dict) else ""
        if not _safe_path(path):
            raise InvalidRecord("files.path", f"unsafe or empty path {path!r}")
        if path in seen:
            raise InvalidRecord("files.path", f"path repeated: {path!r}")
        seen.add(path)
        size = entry.get("size_bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise InvalidRecord("files.size_bytes", f"size of {path!r} must be a whole number >= 0")
        sha = entry.get("sha256")
        if sha in (None, ""):
            sha = None
        elif not (isinstance(sha, str) and _SHA256.match(sha)):
            raise InvalidRecord("files.sha256", f"checksum of {path!r} must be 64 hex characters")
        out.append(
            {
                "path": path,
                "size_bytes": size,
                "sha256": sha,
                "file_type": _text(entry.get("file_type")),
                "safety_scan": _text(entry.get("safety_scan")),
                "downloaded": bool(entry.get("downloaded", False)),
            }
        )
    return out


def _refs(raw, commit: str) -> list[dict]:
    out = []
    for entry in raw or []:
        if entry.get("kind") not in ("branch", "tag") or not entry.get("name"):
            raise InvalidRecord("refs", "each ref needs a name and a kind of branch or tag")
        ref_commit = entry.get("commit") or commit
        if not _COMMIT.match(ref_commit):
            raise InvalidRecord("refs.commit", "must be 40 hex characters")
        out.append({"name": entry["name"], "kind": entry["kind"], "commit": ref_commit})
    return out


def _import_record(raw) -> dict:
    if not isinstance(raw, dict):
        raise InvalidRecord("importRecord", "is required")
    for name in (
        "importedBy",
        "importedAt",
        "computer",
        "bundleName",
        "bundleSha256",
        "signingKeyFingerprint",
        "toolVersion",
        "checkResults",
        "outcome",
    ):
        if raw.get(name) in (None, ""):
            raise InvalidRecord(f"importRecord.{name}", "is required")
    by = raw["importedBy"]
    if not isinstance(by, dict) or not by.get("id") or not by.get("name"):
        raise InvalidRecord("importRecord.importedBy", "needs an id and a name")
    if raw["outcome"] not in OUTCOMES:
        raise InvalidRecord("importRecord.outcome", f"must be one of {OUTCOMES}")
    return {
        "imported_by_id": str(by["id"]),
        "imported_by_name": str(by["name"]),
        "imported_at": parse_time(raw["importedAt"], "importRecord.importedAt", True),
        "computer": str(raw["computer"]),
        "bundle_name": str(raw["bundleName"]),
        "bundle_sha256": str(raw["bundleSha256"]),
        "signing_key_fingerprint": str(raw["signingKeyFingerprint"]),
        "tool_version": str(raw["toolVersion"]),
        "check_results": raw["checkResults"],
        "outcome": raw["outcome"],
    }


def _documents(documents: list[Document]) -> None:
    if len(documents) > MAX_DOCUMENTS:
        raise InvalidRecord("documents", f"at most {MAX_DOCUMENTS} documents per version")
    total = 0
    seen: set[tuple[str, str]] = set()
    for doc in documents:
        if doc.kind not in DOCUMENT_KINDS:
            raise InvalidRecord("document.kind", f"unknown kind {doc.kind!r}")
        if not _safe_path(doc.name):
            raise InvalidRecord("document.name", f"unsafe or empty name {doc.name!r}")
        if len(doc.content) > MAX_DOCUMENT_BYTES:
            raise InvalidRecord("document.size", f"{doc.kind}/{doc.name} is over 16 MiB")
        if (doc.kind, doc.name) in seen:
            raise InvalidRecord("document.name", f"{doc.kind}/{doc.name} is repeated")
        seen.add((doc.kind, doc.name))
        total += len(doc.content)
        if doc.kind == "picture" and doc.picture_status is None:
            doc.picture_status = "stored"
    if total > MAX_DOCUMENT_TOTAL_BYTES:
        raise InvalidRecord("documents", "the documents together are over 64 MiB")


def validate_record(
    model_id: str, commit: str, record: dict, documents: list[Document]
) -> Validated:
    if not model_id or "/" not in model_id.strip("/"):
        raise InvalidRecord("model_id", "a model id like organisation/name is required")
    if not _COMMIT.match(commit or ""):
        raise InvalidRecord("commit", "must be 40 hexadecimal characters")
    raw = record.get("version")
    if not isinstance(raw, dict):
        raise InvalidRecord("version", "is required")
    if raw.get("commit") != commit or (raw.get("model_id") or "").lower() != model_id.lower():
        raise InvalidRecord("commit", "the record does not match the address")
    _documents(documents)
    version = {
        "captured_at": parse_time(raw.get("captured_at"), "captured_at", True),
        "license": _text(raw.get("license")),
        "language": _text_list(raw.get("language"), "language"),
        "tags": _text_list(raw.get("tags"), "tags"),
        "task": _text(raw.get("task")),
        "library": _text(raw.get("library")),
        "parameter_count": _count(raw.get("parameter_count"), "parameter_count"),
        "downloads": _count(raw.get("downloads"), "downloads"),
        "likes": _count(raw.get("likes"), "likes"),
        "size_bytes": _count(raw.get("size_bytes"), "size_bytes"),
        "counts_captured_at": parse_time(raw.get("counts_captured_at"), "counts_captured_at"),
        "created_at": parse_time(raw.get("created_at"), "created_at"),
        "last_modified_at": parse_time(raw.get("last_modified_at"), "last_modified_at"),
    }
    files = _files(raw.get("files", []))
    refs = _refs(raw.get("refs"), commit)
    imp = _import_record(record.get("importRecord"))
    declared = record.get("documentChecksums") or {}
    by_key = {f"{d.kind}/{d.name}": d for d in documents}
    for key, sha in declared.items():
        if key in by_key and by_key[key].sha256 != sha:
            raise InvalidRecord("document.checksum", f"{key} does not match its stated checksum")
    card = next((d for d in documents if d.kind == "readme"), None) or next(
        (d for d in documents if d.kind == "readme_local"), None
    )
    return Validated(
        model_id=model_id,
        commit=commit,
        version=version,
        files=files,
        refs=refs,
        documents=documents,
        import_record=imp,
        has_readme=card is not None,
        card_text=card.content.decode("utf-8", errors="replace") if card else None,
        declared_checksums=declared,
    )


def validate_import_only(model_id: str, commit: str, record: dict) -> dict:
    """An import-only record (a skipped or repaired import): returns the normalised trail fields."""
    if not _COMMIT.match(commit or ""):
        raise InvalidRecord("commit", "must be 40 hexadecimal characters")
    imp = _import_record(record.get("importRecord"))
    if imp["outcome"] not in ("skipped", "repaired"):
        raise InvalidRecord("importRecord.outcome", "an import-only record is skipped or repaired")
    return imp


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def checksum(v: Validated) -> str:
    """SHA-256 of the canonical record and each document's checksum (rule BR1.2)."""
    imp = {k: _iso(x) for k, x in v.import_record.items() if k != "imported_at"}
    body = {
        "format": RECORD_FORMAT,
        "model": v.model_id.lower(),
        "commit": v.commit,
        "version": {k: _iso(x) for k, x in v.version.items()},
        "files": sorted(v.files, key=lambda f: f["path"]),
        "refs": sorted(v.refs, key=lambda r: (r["kind"], r["name"])),
        "import": imp,
        "documents": sorted((d.kind, d.name, d.sha256) for d in v.documents),
    }
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
