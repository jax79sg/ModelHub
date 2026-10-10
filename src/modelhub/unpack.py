"""`unpack`: check a bundle, then rebuild it into the model store (contract C3)."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import shutil
import tarfile
from dataclasses import dataclass
from pathlib import Path

from modelhub import fsutil, record, store, verify
from modelhub.progress import NullReporter

logger = logging.getLogger("modelhub.unpack")

_MAX_MANIFEST = 64 * 1024 * 1024
_ALLOWED_TOP = ("summary.json", "raw/", "readme/")


class UnsafeArchive(Exception):
    """An archive entry that must not be written (escaping path, link, unlisted file)."""


class IntegrityFailure(Exception):
    """A rebuilt file does not match the manifest."""


class JoinedPieces(io.RawIOBase):
    """The pieces read back-to-back as one stream, in index order."""

    def __init__(self, paths: list[Path], on_read=None):
        self._paths = list(paths)
        self._handle = None
        self._next = 0
        self.size = 0
        self.sha256 = hashlib.sha256()
        self.on_read = on_read

    def readable(self) -> bool:
        return True

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None
        super().close()

    def readinto(self, buffer) -> int:
        while True:
            if self._handle is None:
                if self._next >= len(self._paths):
                    return 0
                self._handle = open(self._paths[self._next], "rb")  # noqa: SIM115 - kept open across reads
                self._next += 1
            count = self._handle.readinto(buffer)
            if count:
                self.size += count
                self.sha256.update(memoryview(buffer)[:count])
                if self.on_read:
                    self.on_read(count)
                return count
            self._handle.close()
            self._handle = None


@dataclass
class UnpackResult:
    model_id: str
    commit: str
    path: Path
    already_present: bool = False


def unpack_bundle(dirs: list[Path], store_dir: Path, progress=None) -> list[UnpackResult]:
    progress = progress or NullReporter()
    reports = verify.verify_bundle(dirs, progress=progress)
    if not reports:
        raise verify.VerifyFailed(
            [
                verify.BundleReport(
                    "(none)", problems=[verify.Problem("no-bundle", "no bundle found")]
                )
            ]
        )
    if any(not r.ok for r in reports):
        raise verify.VerifyFailed(reports)
    return [_unpack_one(report, Path(store_dir), progress) for report in reports]


def _unpack_one(report: verify.BundleReport, store_dir: Path, progress) -> UnpackResult:
    model = report.manifest["model"]
    paths = store.StorePaths(store_dir, model["id"])
    final = paths.commit_dir(model["commit"])
    if (final / "summary.json").is_file():
        # A run stopped just after the rename must still leave the pointers right (NFR3.1).
        c1 = json.loads((final / "manifest.json").read_text(encoding="utf-8"))
        store.update_pointers(paths, model["commit"], c1.get("requested_revision", "main"))
        return UnpackResult(model["id"], model["commit"], final, already_present=True)

    if fsutil.case_matters_here(store_dir):
        clash = fsutil.case_conflict(Path(store_dir, "models"), model["id"].split("/"))
        if clash:
            raise UnsafeArchive(
                f"{model['id']} differs only by letter case from {clash!r} already in the store"
            )

    partial = paths.partial_dir(model["commit"])
    with fsutil.RunLock(paths.model_dir):
        joined = JoinedPieces(report.piece_paths, on_read=progress.advance)
        reader = io.BufferedReader(joined, 1 << 20)
        progress.start(f"Rebuilding {model['id']}", total_bytes=report.manifest["stream"]["size"])
        try:
            with progress.running():
                requested = _extract(
                    reader, partial, report.manifest, fsutil.case_matters_here(store_dir)
                )
                _finish_stream(reader, joined, report.manifest)
        except (UnsafeArchive, IntegrityFailure, fsutil.UnsafePathError):
            shutil.rmtree(partial, ignore_errors=True)  # a refused bundle leaves nothing behind
            raise
        finally:
            reader.close()
            progress.finish()
        os.replace(partial, final)
        store.update_pointers(paths, model["commit"], requested)
    logger.info("unpacked %s %s into %s", model["id"], model["commit"][:12], final)
    return UnpackResult(model["id"], model["commit"], final)


def _extract(reader, partial: Path, manifest: dict, ignore_case: bool = False) -> str:
    expected: dict[str, dict] = {}
    declared = manifest["stream"]["size"]
    requested = "main"
    with tarfile.open(fileobj=reader, mode="r|") as tar:
        first = tar.next()
        if first is None or first.name != "manifest.json" or not first.isreg():
            raise UnsafeArchive("the archive does not start with manifest.json")
        if first.size > _MAX_MANIFEST:
            raise UnsafeArchive("manifest.json is unreasonably large")
        data = tar.extractfile(first).read()
        if hashlib.sha256(data).hexdigest() != manifest["c1_manifest_sha256"]:
            raise IntegrityFailure(
                "manifest.json inside the archive is not the one that was signed"
            )
        c1 = json.loads(data)
        record.check_format_version(c1.get("format_version", "0"))
        requested = c1.get("requested_revision", "main")
        expected = {f"files/{entry['path']}": entry for entry in c1["files"]}
        if ignore_case:
            folded: dict[str, str] = {}
            for name in expected:
                if folded.setdefault(name.casefold(), name) != name:
                    raise UnsafeArchive(
                        f"{name} and {folded[name.casefold()]} differ only by letter case"
                    )
        fsutil.atomic_write_bytes(fsutil.safe_join(partial, "manifest.json"), data)

        seen: set[str] = set()
        while (member := tar.next()) is not None:
            if tar.offset > declared:
                raise UnsafeArchive("the archive is longer than the signed manifest declares")
            _write_member(tar, member, partial, expected)
            seen.add(member.name)
        missing = sorted(set(expected) - seen)
        if missing:
            raise IntegrityFailure(f"files missing from the archive: {', '.join(missing)}")
    return requested


def _write_member(
    tar: tarfile.TarFile, member: tarfile.TarInfo, partial: Path, expected: dict
) -> None:
    name = member.name
    if not member.isreg():
        raise UnsafeArchive(f"{name}: only plain files are allowed in a bundle")
    wanted = expected.get(name)
    if name.startswith("files/"):
        if wanted is None or wanted["size"] != member.size:
            raise UnsafeArchive(f"{name}: not listed in the manifest")
    elif not any(
        name == top or (top.endswith("/") and name.startswith(top)) for top in _ALLOWED_TOP
    ):
        raise UnsafeArchive(f"{name}: unexpected entry in the archive")
    dest = fsutil.safe_join(partial, name)
    if (
        wanted
        and dest.is_file()
        and dest.stat().st_size == wanted["size"]
        and (fsutil.sha256_file(dest) == wanted["sha256"])
    ):
        return  # rebuilt and checked on an earlier run: not written again (NFR3.4)
    source = tar.extractfile(member)
    with fsutil.AtomicFile(dest) as out:
        shutil.copyfileobj(source, out, 1 << 20)
        if wanted and out.sha256 != wanted["sha256"]:
            raise IntegrityFailure(f"{name}: does not match its checksum in the manifest")


def _finish_stream(reader, joined: JoinedPieces, manifest: dict) -> None:
    while reader.read(1 << 20):
        pass
    stream = manifest["stream"]
    if joined.size != stream["size"] or joined.sha256.hexdigest() != stream["sha256"]:
        raise IntegrityFailure("the pieces joined together do not match the signed manifest")
