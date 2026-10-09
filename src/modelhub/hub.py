"""Online side: fetch a repo snapshot plus Hub metadata."""
import dataclasses
import json
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download

from modelhub.manifest import METADATA_DIR, SNAPSHOT_DIR, Manifest, build_manifest


def _jsonable(obj):
    return json.loads(json.dumps(dataclasses.asdict(obj), default=str))


def pull(
    repo_id: str,
    out: Path,
    repo_type: str = "model",
    revision: str = "main",
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    token: str | None = None,
) -> tuple[Path, Manifest]:
    """Download `repo_id` pinned to its resolved commit into `out/<repo_id>/`."""
    api = HfApi(token=token)
    info = api.repo_info(repo_id, revision=revision, repo_type=repo_type, files_metadata=True)

    root = out / repo_id
    (root / METADATA_DIR).mkdir(parents=True, exist_ok=True)
    (root / METADATA_DIR / "repo_info.json").write_text(json.dumps(_jsonable(info), indent=2))
    # Commit history is useful provenance for the on-prem registry.
    refs = api.list_repo_refs(repo_id, repo_type=repo_type)
    (root / METADATA_DIR / "refs.json").write_text(json.dumps(_jsonable(refs), indent=2))

    # Pin to the commit sha so a moving branch can't change files mid-download.
    snapshot_download(
        repo_id,
        repo_type=repo_type,
        revision=info.sha,
        local_dir=root / SNAPSHOT_DIR,
        allow_patterns=include,
        ignore_patterns=exclude,
        token=token,
    )

    manifest = build_manifest(root, repo_id, repo_type, info.sha, revision)
    _check_against_hub(manifest, info)
    (root / "manifest.json").write_text(manifest.to_json())
    return root, manifest


def _check_against_hub(manifest: Manifest, info) -> None:
    """LFS files expose a sha256 on the Hub; make sure what we hashed matches it."""
    for s in info.siblings or []:
        lfs = getattr(s, "lfs", None)
        entry = manifest.files.get(f"{SNAPSHOT_DIR}/{s.rfilename}")
        if lfs and entry and lfs.sha256 != entry["sha256"]:
            raise RuntimeError(f"Hub sha256 mismatch for {s.rfilename}")
