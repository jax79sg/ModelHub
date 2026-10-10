"""`bundle`: check a download record against its manifest, then write signed pieces (C2)."""

from __future__ import annotations

import hashlib
import json
import logging
import tarfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from modelhub import __version__, fsutil, pieces, record, signing
from modelhub.progress import NullReporter

logger = logging.getLogger("modelhub.bundle")

RESERVE = 256 * 1024  # room left on each interactive drive for the manifest and signature
_SKIP = {".modelhub.lock", ".modelhub-dl"}


class RecordChanged(Exception):
    """The record on disk is not what `pull` wrote: it may differ from what was scanned."""

    def __init__(self, problems: list[str]):
        super().__init__(
            "the download record changed since it was pulled:\n  " + "\n  ".join(problems)
        )
        self.problems = problems


class InsufficientSpace(Exception):
    pass


class TooManyPieces(Exception):
    pass


@dataclass
class BundleResult:
    stem: str
    pieces: list[dict]
    manifest_path: Path
    stream_size: int


def check_record(root: Path) -> dict:
    """Prove the files are exactly what the download manifest lists (so what was scanned is
    what gets packed)."""
    manifest = record.load_manifest(root / "manifest.json")
    problems = []
    listed = set()
    for entry in manifest["files"]:
        listed.add(entry["path"])
        path = root / "files" / entry["path"]
        if not path.is_file():
            problems.append(f"missing: {entry['path']}")
        elif path.stat().st_size != entry["size"] or fsutil.sha256_file(path) != entry["sha256"]:
            problems.append(f"changed: {entry['path']}")
    on_disk = {
        p.relative_to(root / "files").as_posix() for p in (root / "files").rglob("*") if p.is_file()
    }
    problems += [f"not in manifest: {name}" for name in sorted(on_disk - listed)]
    if problems:
        raise RecordChanged(problems)
    return manifest


def record_members(root: Path) -> list[tuple[str, Path]]:
    """What goes into the archive, in a fixed order: manifest first, so unpacking can check
    every later file against it."""
    members = [("manifest.json", root / "manifest.json")]
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file() or rel.parts[0] in _SKIP or rel.name.endswith(".partial"):
            continue
        if rel.as_posix() != "manifest.json":
            members.append((rel.as_posix(), path))
    return members


def _tarinfo(arcname: str, path: Path) -> tarfile.TarInfo:
    info = tarfile.TarInfo(arcname)
    stat = path.stat()
    info.size = stat.st_size
    info.mtime = int(stat.st_mtime)
    info.mode = 0o644
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def tar_stream_size(members: list[tuple[str, Path]]) -> int:
    """The exact size of the archive, worked out without reading any file."""
    total = 0
    for arcname, path in members:
        info = _tarinfo(arcname, path)
        total += len(info.tobuf(tarfile.PAX_FORMAT, "utf-8", "surrogateescape"))
        total += -(-info.size // 512) * 512
    total += 1024
    return -(-total // tarfile.RECORDSIZE) * tarfile.RECORDSIZE


def plan_bundle(record_dir: Path, piece_size: int) -> tuple[int, int]:
    """The total size and the number of pieces, stated before anything is written (FR6.7)."""
    size = tar_stream_size(record_members(Path(record_dir)))
    return size, -(-size // piece_size)


class SliceWriter:
    """Receives the archive bytes and cuts them into pieces, each written under a temporary
    name and renamed when complete."""

    def __init__(
        self,
        stem: str,
        next_slot: Callable[[int], tuple[Path, int]],
        on_piece=None,
        on_bytes=None,
    ):
        self.stem = stem
        self.next_slot = next_slot
        self.on_piece = on_piece
        self.on_bytes = on_bytes
        self.pieces: list[dict] = []
        self.stream = hashlib.sha256()
        self.size = 0
        self._current = None
        self._limit = 0
        self.last_dir: Path | None = None

    def _open(self) -> None:
        index = len(self.pieces) + 1
        if index > pieces.MAX_PIECES:
            raise TooManyPieces(f"a bundle can have at most {pieces.MAX_PIECES} pieces")
        self.last_dir, self._limit = self.next_slot(index)
        name = pieces.piece_name(self.stem, index)
        self._current = fsutil.AtomicFile(self.last_dir / name)
        self._current.__enter__()

    def _close(self) -> None:
        current, self._current = self._current, None
        current.__exit__(None, None, None)
        index = len(self.pieces) + 1
        self.pieces.append(
            {
                "index": index,
                "name": pieces.piece_name(self.stem, index),
                "size": current.size,
                "sha256": current.sha256,
                "offset": self.size - current.size,
            }
        )
        if self.on_piece:
            self.on_piece(self.pieces[-1], self.last_dir)

    def write(self, data: bytes) -> int:
        view = memoryview(data)
        while len(view):
            if self._current is None:
                self._open()
            take = view[: self._limit - self._current.size]
            self._current.write(take)
            self.stream.update(take)
            self.size += len(take)
            if self.on_bytes:
                self.on_bytes(len(take))
            view = view[len(take) :]
            if self._current.size == self._limit:
                self._close()
        return len(data)

    def finish(self) -> None:
        if self._current is not None:
            self._close()

    def abort(self) -> None:
        if self._current is not None:
            current, self._current = self._current, None
            current.__exit__(RuntimeError, RuntimeError("aborted"), None)


def _manifest_doc(
    c1: dict, c1_sha: str, key_id: str, writer: SliceWriter, piece_size, complete: bool, now: str
) -> dict:
    return {
        "format_version": record.FORMAT_VERSION,
        "tool_version": __version__,
        "created_at": now,
        "complete": complete,
        "model": {"id": c1["model_id"], "commit": c1["commit"], "captured_at": c1["captured_at"]},
        "key_id": key_id,
        "c1_manifest_sha256": c1_sha,
        "stream": {"archive": "pax-tar", "size": writer.size, "sha256": writer.stream.hexdigest()},
        "piece_size_max": piece_size,
        "pieces": list(writer.pieces),
    }


def _write_manifest(directory: Path, stem: str, doc: dict, key_id: str) -> Path:
    path = directory / f"{stem}.bundle.json"
    data = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fsutil.atomic_write_bytes(path, data)
    sig = signing.sign_bytes(key_id, data)
    fsutil.atomic_write_text(directory / f"{stem}.bundle.sig", json.dumps(sig, indent=2) + "\n")
    return path


def bundle_record(
    record_dir: Path,
    out_dir: Path,
    key_id: str,
    piece_size: int | None = None,
    next_drive: Callable[[int], tuple[Path, int]] | None = None,
    now=record.utc_now,
    progress=None,
) -> BundleResult:
    record_dir, out_dir = Path(record_dir), Path(out_dir)
    progress = progress or NullReporter()
    if (piece_size is None) == (next_drive is None):
        raise ValueError("give either a piece size or an interactive drive callback")
    if piece_size is not None and piece_size < pieces.MIN_PIECE_SIZE:
        raise ValueError(f"piece size must be at least {pieces.MIN_PIECE_SIZE} bytes")

    c1 = check_record(record_dir)
    c1_sha = fsutil.sha256_file(record_dir / "manifest.json")
    members = record_members(record_dir)
    size = tar_stream_size(members)
    if piece_size is not None:
        if size > pieces.MAX_PIECES * piece_size:
            raise TooManyPieces(
                f"{-(-size // piece_size)} pieces needed; at most {pieces.MAX_PIECES}"
            )
        out_dir.mkdir(parents=True, exist_ok=True)
        if fsutil.free_bytes(out_dir) < size:
            raise InsufficientSpace(
                f"{size} bytes needed in {out_dir}, {fsutil.free_bytes(out_dir)} free"
            )

    stem = pieces.stem_for(c1["model_id"], c1["commit"])
    stamp = now()

    def next_slot(index: int) -> tuple[Path, int]:
        if next_drive is None:
            return out_dir, piece_size
        directory, capacity = next_drive(index)
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        if capacity <= RESERVE:
            raise InsufficientSpace(f"a drive of {capacity} bytes is too small to hold a piece")
        return directory, capacity - RESERVE

    def on_piece(piece: dict, directory: Path) -> None:
        logger.info(
            "wrote piece %d (%s, %d bytes) in %s",
            piece["index"],
            piece["name"],
            piece["size"],
            directory,
        )
        if next_drive is not None:  # a provisional manifest on each drive, in case it is used alone
            _write_manifest(
                directory,
                stem,
                _manifest_doc(c1, c1_sha, key_id, writer, None, False, stamp),
                key_id,
            )

    writer = SliceWriter(stem, next_slot, on_piece, on_bytes=progress.advance)
    progress.start(f"Writing pieces for {c1['model_id']}", total_bytes=size)
    try:
        with progress.running():
            with tarfile.open(fileobj=writer, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                for arcname, path in members:
                    with open(path, "rb") as handle:
                        tar.addfile(_tarinfo(arcname, path), handle)
            writer.finish()
    except BaseException:
        writer.abort()
        raise
    finally:
        progress.finish()

    doc = _manifest_doc(c1, c1_sha, key_id, writer, piece_size, True, stamp)
    manifest_path = _write_manifest(writer.last_dir or out_dir, stem, doc, key_id)
    logger.info("bundle %s complete: %d pieces, %d bytes", stem, len(writer.pieces), writer.size)
    return BundleResult(stem, writer.pieces, manifest_path, writer.size)
