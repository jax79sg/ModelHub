"""The stable summary the web app reads (contract C3, summary.json).

Anything Hugging Face did not give is null, never 0 or an empty string, so 'unknown' and
'zero' stay different things.
"""

from __future__ import annotations

from modelhub import __version__, filetypes
from modelhub.record import FORMAT_VERSION


def _licence_file(files: list[dict]) -> str | None:
    candidates = [f["path"] for f in files if filetypes.classify(f["path"]).key == "licence"]
    if not candidates:
        return None
    return "files/" + min(candidates, key=lambda p: (p.count("/"), p))


def build_summary(
    info: dict,
    manifest: dict,
    captured_at: str,
    readme_local: str | None = None,
    pictures: list[dict] | None = None,
) -> dict:
    card = info.get("cardData") or {}
    files = manifest["files"]
    licence_name = card.get("license")
    licence_file = _licence_file(files)
    has_readme = any(f["path"] == "README.md" for f in files)
    return {
        "format_version": FORMAT_VERSION,
        "tool_version": __version__,
        "model_id": manifest["model_id"],
        "commit": manifest["commit"],
        "captured_at": captured_at,
        "card": {
            "license": licence_name,
            "language": card.get("language"),
            "tags": info.get("tags") or [],
            "pipeline_tag": info.get("pipeline_tag"),
            "library_name": info.get("library_name"),
        },
        "stats": {
            "downloads": info.get("downloads"),
            "likes": info.get("likes"),
            "used_storage_bytes": info.get("usedStorage"),
            "parameter_counts": info.get("safetensors"),
        },
        "created_at": info.get("createdAt"),
        "last_modified": info.get("lastModified"),
        "size_bytes": sum(f["size"] for f in files),
        "license": {
            "name": licence_name,
            "file": licence_file,
            "text_available": licence_file is not None,
        },
        "readme": {
            "original": "files/README.md" if has_readme else None,
            "local": readme_local,
            "pictures": pictures or [],
        },
        "files": [
            {
                "path": f["path"],
                "size": f["size"],
                "sha256": f["sha256"],
                "type": filetypes.classify(f["path"]).key,
                "scan": f.get("scan"),
            }
            for f in files
        ],
        "history": {"commits_file": "raw/commits.json", "refs_file": "raw/refs.json"},
    }
