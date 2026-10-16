"""Build the Catalog's version record and documents from an unpacked bundle (rule BR1.8; C2, C3).

The unpacked folder has the layout of the model store (``summary.json``, ``manifest.json``,
``raw/``, ``readme/``, ``files/``). Anything the Hub did not give stays null, never 0 or empty
text (FR2.4).
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
from pathlib import Path

_TYPES = {".json": "application/json", ".md": "text/markdown", ".txt": "text/plain"}


def _content_type(name: str) -> str:
    suffix = Path(name).suffix.lower()
    return _TYPES.get(suffix) or mimetypes.guess_type(name)[0] or "application/octet-stream"


def _text(value) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, list):
        return ", ".join(str(x) for x in value) or None
    return str(value)


def _scan(value) -> str | None:
    if isinstance(value, dict):
        return _text(value.get("status"))
    return _text(value)


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _files(out: Path, summary: dict) -> list[dict]:
    files = [
        {
            "path": f["path"],
            "size_bytes": f["size"],
            "sha256": f.get("sha256"),
            "file_type": f.get("type"),
            "safety_scan": _scan(f.get("scan")),
            "downloaded": True,
        }
        for f in summary.get("files", [])
    ]
    have = {f["path"] for f in files}
    for entry in _read_json(out / "raw" / "tree.json") or []:
        path = entry.get("path", "")
        if entry.get("type") != "file" or not path or path in have:
            continue
        lfs = entry.get("lfs") or {}
        files.append(
            {
                "path": path,
                "size_bytes": int(entry.get("size", 0)),
                "sha256": lfs.get("oid"),
                "file_type": None,
                "safety_scan": _scan(entry.get("securityFileStatus") or {}),
                "downloaded": False,
            }
        )
    return files


def _refs(out: Path, commit: str) -> list[dict]:
    raw = _read_json(out / "raw" / "refs.json") or {}
    refs = []
    for kind, key in (("branch", "branches"), ("tag", "tags")):
        for entry in raw.get(key, []):
            if entry.get("name"):
                refs.append(
                    {
                        "name": entry["name"],
                        "kind": kind,
                        "commit": entry.get("targetCommit") or commit,
                    }
                )
    return refs


def _documents(out: Path, summary: dict, description: Path, signature: Path) -> list[tuple]:
    docs: list[tuple[str, bytes, str]] = []

    def add(kind: str, name: str, path: Path, ctype: str | None = None) -> None:
        if path.is_file():
            docs.append((f"{kind}/{name}", path.read_bytes(), ctype or _content_type(name)))

    add("readme", "README.md", out / "files" / "README.md", "text/markdown")
    readme = summary.get("readme") or {}
    if readme.get("local"):
        add("readme_local", "README.local.md", out / readme["local"], "text/markdown")
    for index, picture in enumerate(readme.get("pictures") or []):
        local = picture.get("local")
        if local and (out / local).is_file():
            add("picture", Path(local).name, out / local)
        else:
            source = str(picture.get("source", index))
            name = "unfetched-" + hashlib.sha256(source.encode()).hexdigest()[:16]
            docs.append((f"picture/{name}", b"", "application/octet-stream"))
    licence = (summary.get("license") or {}).get("file")
    if licence:
        add("licence", Path(licence).name, out / licence)
    add("response", "summary.json", out / "summary.json", "application/json")
    add("manifest", "manifest.json", out / "manifest.json", "application/json")
    raw = out / "raw"
    if raw.is_dir():
        for path in sorted(raw.glob("*.json")):
            add("response", f"raw/{path.name}", path, "application/json")
    add("bundle_description", description.name, description, "application/json")
    add("bundle_signature", signature.name, signature, "application/json")
    return docs


def import_record(job: dict, description_bytes: bytes) -> dict:
    """The trail entry for one import (C2 ``importRecord``)."""
    return {
        "importedBy": {"id": job["imported_by_id"], "name": job["imported_by_name"]},
        "importedAt": job["imported_at"],
        "computer": job["computer"],
        "bundleName": job["bundle_name"],
        "bundleSha256": hashlib.sha256(description_bytes).hexdigest(),
        "signingKeyFingerprint": job["signing_key_fingerprint"],
        "toolVersion": job["tool_version"],
        "checkResults": job["check_results"],
        "outcome": job["outcome"],
    }


def build_record(
    out: Path, job: dict, description: Path, signature: Path
) -> tuple[dict, list[tuple[str, bytes, str]]]:
    """The record and documents for ``PUT`` to the Catalog. ``job`` holds who imported and how."""
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    card = summary.get("card") or {}
    stats = summary.get("stats") or {}
    counts = stats.get("parameter_counts") or {}
    commit = summary["commit"]
    version = {
        "model_id": summary["model_id"],
        "commit": commit,
        "captured_at": summary["captured_at"],
        "license": _text(card.get("license")),
        "language": card.get("language"),
        "tags": card.get("tags"),
        "task": card.get("pipeline_tag"),
        "library": card.get("library_name"),
        "parameter_count": counts.get("total") if isinstance(counts, dict) else None,
        "downloads": stats.get("downloads"),
        "likes": stats.get("likes"),
        "size_bytes": summary.get("size_bytes"),
        "counts_captured_at": summary["captured_at"],
        "created_at": summary.get("created_at"),
        "last_modified_at": summary.get("last_modified"),
        "refs": _refs(out, commit),
        "files": _files(out, summary),
    }
    imp = import_record(job, description.read_bytes())
    return {"version": version, "importRecord": imp}, _documents(
        out, summary, description, signature
    )
