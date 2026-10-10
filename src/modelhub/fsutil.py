"""Small file helpers shared by every command: atomic writes, hashing, safe paths, locking."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import sys
from pathlib import Path

BLOCK = 1 << 20  # files are always read in blocks, never whole (NFR1.3, NFR1.4)
IS_WINDOWS = sys.platform == "win32"

_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_FORBIDDEN = set('<>:"|?*')
_MAX_COMPONENT = 255
_MAX_PATH = 240  # leaves room for the folder the file is written into (Windows allows 260)


def windows_name_problems(rel: str) -> list[str]:
    """Reasons a repository path cannot be written on Windows; empty when it can (FR6.8, NFR7.5).
    Such files are reported by name and never silently renamed."""
    problems = []
    if len(rel) > _MAX_PATH:
        problems.append(f"path too long ({len(rel)} characters; limit {_MAX_PATH})")
    for part in rel.replace("\\", "/").split("/"):
        stem = part.split(".")[0].upper()
        if stem in _RESERVED:
            problems.append(f"{part!r} is a reserved name on Windows")
        if any(ch in _FORBIDDEN or ord(ch) < 32 for ch in part):
            problems.append(f"{part!r} has a forbidden character")
        if part and part[-1] in ". ":
            problems.append(f"{part!r} ends with a dot or space")
        if len(part) > _MAX_COMPONENT:
            problems.append(f"name too long ({len(part)} characters; limit {_MAX_COMPONENT})")
    return problems


class UnsafePathError(ValueError):
    """A path that would leave the folder it must stay inside."""


class LockedError(RuntimeError):
    """Another run already holds this folder."""


def sha256_file(path: Path | str, block: int = BLOCK, on_block=None) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(block):
            digest.update(chunk)
            if on_block:
                on_block(len(chunk))
    return digest.hexdigest()


def git_blob_sha1(path: Path | str, block: int = BLOCK) -> str:
    """The checksum git (and so the Hub) reports for an ordinary, non-LFS file."""
    digest = hashlib.sha1(b"blob %d\0" % os.path.getsize(path))
    with open(path, "rb") as handle:
        while chunk := handle.read(block):
            digest.update(chunk)
    return digest.hexdigest()


def _partial_name(path: Path) -> Path:
    return path.with_name(f".{path.name}.partial")


def atomic_write_bytes(path: Path | str, data: bytes) -> None:
    with AtomicFile(path) as handle:
        handle.write(data)


def atomic_write_text(path: Path | str, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


class AtomicFile:
    """Write to a temporary name and rename when finished, so a stopped run never leaves a
    half-written file that looks complete (FR6.6, NFR3.1)."""

    def __init__(self, path: Path | str, keep_if_same_as: str | None = None):
        self.path = Path(path)
        self.tmp = _partial_name(self.path)
        self.keep_if_same_as = keep_if_same_as
        self._sha = hashlib.sha256()
        self.size = 0
        self._handle = None

    def __enter__(self) -> AtomicFile:  # noqa: PYI034 - typing.Self needs Python 3.11
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = open(self.tmp, "wb")
        return self

    def write(self, data: bytes) -> int:
        self._handle.write(data)
        self._sha.update(data)
        self.size += len(data)
        return len(data)

    @property
    def sha256(self) -> str:
        return self._sha.hexdigest()

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._handle.flush()
        os.fsync(self._handle.fileno())
        self._handle.close()
        try:
            if exc_type is None:
                if self._unchanged():
                    self.tmp.unlink()
                else:
                    os.replace(self.tmp, self.path)
        finally:
            if self.tmp.exists():
                self.tmp.unlink()
        return False

    def _unchanged(self) -> bool:
        """True when the file already on disk is byte-for-byte what was just written."""
        if not self.path.is_file() or self.path.stat().st_size != self.size:
            return False
        return sha256_file(self.path) == self.sha256


_DRIVE_PATH = re.compile(r"^[A-Za-z]:[\\/]")  # C:\x or C:/x looks absolute everywhere
_DRIVE_LETTER = re.compile(r"^[A-Za-z]:")  # C:x is relative to a drive, which matters on Windows


def safe_join(root: Path | str, rel: str) -> Path:
    """Join `rel` onto `root`, refusing anything that would land outside it (NFR2.10)."""
    if "\x00" in rel:
        raise UnsafePathError(f"unsafe path: {rel!r}")
    normalized = rel.replace("\\", "/")
    if (
        normalized.startswith("/")
        or _DRIVE_PATH.match(rel)
        or (IS_WINDOWS and _DRIVE_LETTER.match(rel))
    ):
        raise UnsafePathError(f"absolute path not allowed: {rel!r}")
    if ".." in normalized.split("/"):
        raise UnsafePathError(f"path escapes its folder: {rel!r}")
    base = Path(root).resolve()
    # The name has no "..", so only a link inside the folder could lead out of it. Look for links
    # directly instead of resolving the new path a second time: on Windows that second answer can
    # be spelled differently (8.3 short names) while files are being written at once.
    current = base
    for part in normalized.split("/"):
        if part in ("", "."):
            continue
        current = current / part
        if current.is_symlink() or getattr(os.path, "isjunction", lambda _: False)(current):
            raise UnsafePathError(f"path escapes its folder: {rel!r}")
    return base / normalized


def free_bytes(path: Path | str) -> int:
    probe = Path(path)
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return shutil.disk_usage(probe).free


def is_case_insensitive(folder: Path | str) -> bool:
    """True when this folder is on a file system that ignores letter case (Windows, usually macOS)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    probe = folder / f".CaseProbe-{os.getpid()}"
    probe.write_bytes(b"")
    try:
        return (folder / probe.name.lower()).exists()
    finally:
        probe.unlink()


def case_matters_here(folder: Path | str) -> bool:
    return IS_WINDOWS or is_case_insensitive(folder)


def case_conflict(root: Path | str, parts: list[str]) -> str | None:
    """The name already on disk that differs from one of `parts` only by letter case (NFR7.6)."""
    current = Path(root)
    for part in parts:
        if not current.is_dir():
            return None
        names = [entry.name for entry in os.scandir(current)]
        if part in names:
            current = current / part
            continue
        clash = next((n for n in names if n.casefold() == part.casefold()), None)
        if clash:
            return clash
        return None
    return None


class RunLock:
    """Only one run may use a folder at a time. The lock belongs to the process, so a run
    that was killed never leaves a lock behind (NFR3.7, NFR3.1)."""

    def __init__(self, folder: Path | str):
        self.folder = Path(folder)
        self.path = self.folder / ".modelhub.lock"
        self._handle = None

    def __enter__(self) -> RunLock:  # noqa: PYI034 - typing.Self needs Python 3.11
        self.folder.mkdir(parents=True, exist_ok=True)
        self._handle = open(self.path, "a+b")
        try:
            _lock(self._handle)
        except OSError as error:
            self._handle.close()
            raise LockedError(f"another run is using {self.folder}") from error
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        _unlock(self._handle)
        self._handle.close()
        return False


if sys.platform == "win32":  # pragma: no cover - exercised by the Windows checks
    import msvcrt

    def _lock(handle) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock(handle) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _lock(handle) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(handle) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
