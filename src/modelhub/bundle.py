"""Pack/unpack a pulled repo for physical transfer, and restore it on-prem."""
import shutil
import tarfile
from pathlib import Path

from modelhub.manifest import MANIFEST_NAME, SNAPSHOT_DIR, Manifest, verify_dir


def make_bundle(root: Path, output: Path) -> Path:
    problems = verify_dir(root)
    if problems:
        raise RuntimeError("refusing to bundle a corrupt repo:\n" + "\n".join(problems))
    # Uncompressed: model weights don't compress and it keeps CPU cost off the transfer host.
    with tarfile.open(output, "w") as tar:
        tar.add(root / MANIFEST_NAME, arcname=MANIFEST_NAME)
        for rel in Manifest.load(root).files:
            tar.add(root / rel, arcname=rel)
    return output


def extract_bundle(bundle: Path, dest: Path) -> Path:
    """Extract into `dest` and verify; removes the extraction if verification fails."""
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(bundle) as tar:
        tar.extractall(dest, filter="data")  # rejects absolute paths / traversal
    problems = verify_dir(dest)
    if problems:
        shutil.rmtree(dest)
        raise RuntimeError("bundle failed verification:\n" + "\n".join(problems))
    return dest


def install_hf_cache(root: Path, cache_dir: Path) -> Path:
    """Lay the snapshot out as a Hugging Face hub cache so `from_pretrained` works with
    HF_HUB_CACHE=<cache_dir> HF_HUB_OFFLINE=1."""
    m = Manifest.load(root)
    prefix = {"model": "models", "dataset": "datasets", "space": "spaces"}[m.repo_type]
    repo_dir = cache_dir / f"{prefix}--{m.repo_id.replace('/', '--')}"
    snap = repo_dir / "snapshots" / m.revision
    for rel in m.files:
        if rel.startswith(SNAPSHOT_DIR + "/"):
            target = snap / rel[len(SNAPSHOT_DIR) + 1 :]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / rel, target)
    (repo_dir / "refs").mkdir(parents=True, exist_ok=True)
    (repo_dir / "refs" / m.requested_revision).write_text(m.revision)
    return repo_dir
