"""The signed server pack: a folder of images and files carried across the air gap.

``SHA256SUMS`` lists every file in the pack with its checksum; ``SHA256SUMS.sig`` is the same
kind of signature the bundles carry. On the server the pack is verified against a trusted key
before anything in it is loaded (infrastructure design, first install step 3).
"""

from __future__ import annotations

import json
from pathlib import Path

from modelhub import fsutil, signing

SUMS = "SHA256SUMS"
SIG = "SHA256SUMS.sig"


def _files(folder: Path) -> list[str]:
    return sorted(
        path.relative_to(folder).as_posix()
        for path in folder.rglob("*")
        if path.is_file() and path.name not in (SUMS, SIG) and not path.name.startswith(".")
    )


def sign_pack(folder: Path | str, signer: str) -> int:
    """List every file with its checksum and sign the list. Returns the number of files."""
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"{folder} is not a folder")
    key = signing.find_own_key(signer)  # by id or fingerprint, as the command says
    names = _files(folder)
    lines = [f"{fsutil.sha256_file(folder / name)}  {name}\n" for name in names]
    sums = "".join(lines).encode("utf-8")
    fsutil.atomic_write_bytes(folder / SUMS, sums)
    fsutil.atomic_write_text(
        folder / SIG, json.dumps(signing.sign_bytes(key["key_id"], sums)) + "\n"
    )
    return len(names)


def verify_pack(folder: Path | str) -> list[str]:
    """Everything wrong with the pack, in plain words; an empty list means it can be trusted."""
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"{folder} is not a folder")
    sums_path, sig_path = folder / SUMS, folder / SIG
    if not sums_path.is_file() or not sig_path.is_file():
        return [f"The pack has no signature ({SUMS} and {SIG} are needed)."]
    sums = sums_path.read_bytes()
    try:
        sig_doc = json.loads(sig_path.read_text(encoding="utf-8"))
    except ValueError:
        sig_doc = None
    try:
        signing.verify_signature(sig_doc, sums)
    except signing.SignatureProblem as problem:
        return [f"The signature is not accepted: {problem}"]
    problems: list[str] = []
    listed: set[str] = set()
    for line in sums.decode("utf-8", errors="replace").splitlines():
        digest, _, name = line.partition("  ")
        if len(digest) != 64 or not name:
            problems.append(f"A line in {SUMS} is not readable: {line[:60]!r}")
            continue
        try:
            target = fsutil.safe_join(folder, name)
        except fsutil.UnsafePathError:
            problems.append(f"{name}: unsafe path in the list")
            continue
        listed.add(name)
        if not target.is_file():
            problems.append(f"{name}: missing from the pack")
        elif fsutil.sha256_file(target) != digest:
            problems.append(f"{name}: does not match its checksum")
    for name in _files(folder):
        if name not in listed:
            problems.append(f"{name}: not in the signed list")
    return problems
