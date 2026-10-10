"""Limits of scale (NFR1.7 to NFR1.11): a big store, the piece-count ceiling, huge files."""

import json
import subprocess
import sys
import time
import types

import pytest

from modelhub import bundle, pieces, record, store, unpack, verify


def sparse_file(path, size):
    """Make `path` a file of `size` bytes that uses (almost) no disk. Windows must be told to."""
    with open(path, "wb") as handle:
        if sys.platform == "win32":  # NTFS fills a stretched file with real zeros unless flagged
            subprocess.run(["fsutil", "sparse", "setflag", str(path)], check=True)
        handle.truncate(size)


def make_record(tmp_path, size, model="org/big"):
    """A download record holding one sparse file of `size` bytes (no real disk used)."""
    paths = record.RecordPaths(tmp_path / "work", model, "d" * 40)
    paths.files.mkdir(parents=True)
    try:
        sparse_file(paths.files / "big.bin", size)
    except OSError:
        pytest.skip("this file system cannot make a file that large")
    return paths


def with_manifest(paths):
    manifest = record.new_manifest(
        paths.model_id,
        paths.commit,
        "main",
        record.build_file_entries(paths.files, {}),
        "2026-01-01T00:00:00Z",
    )
    record.write_manifest(paths, manifest)
    return paths


class PretendFile:
    """Stands in for a file of a given size, so no disk is used at all."""

    def __init__(self, size):
        self._size = size

    def stat(self):
        return types.SimpleNamespace(st_size=self._size, st_mtime=0)


def test_a_terabyte_file_is_planned_without_reading_it():
    one_tib = 1_099_511_627_776
    started = time.monotonic()
    size = bundle.tar_stream_size([("big.bin", PretendFile(one_tib))])
    count = -(-size // 1_000_000_000)
    assert size > one_tib
    assert 1000 < count < 1200
    assert time.monotonic() - started < 2  # worked out from sizes alone
    # the piece-count ceiling is far above what a terabyte needs at the smallest piece size
    assert -(-size // pieces.MIN_PIECE_SIZE) > pieces.MAX_PIECES


class StopHere(Exception):
    """Raised by the test to end a bundle right after the checks pass."""


def test_999999_pieces_are_allowed_and_one_more_is_refused(tmp_path, key_id, monkeypatch):
    piece_size = 1024
    limit = pieces.MAX_PIECES * piece_size
    # find a file size whose archive is just inside the limit
    paths = make_record(tmp_path, 1024)
    (paths.root / "manifest.json").write_text("{}")
    overhead = bundle.plan_bundle(paths.root, piece_size)[0] - 1024
    inside = limit - overhead - 10_240
    while True:
        sparse_file(paths.files / "big.bin", inside)
        if bundle.plan_bundle(paths.root, piece_size)[0] > limit:
            inside -= 512
            continue
        break
    sparse_file(paths.files / "big.bin", inside)
    with_manifest(paths)

    def stop(self, data):
        raise StopHere

    monkeypatch.setattr(bundle.SliceWriter, "write", stop)
    out = tmp_path / "out"
    assert bundle.plan_bundle(paths.root, piece_size)[1] <= pieces.MAX_PIECES
    with pytest.raises(StopHere):  # the checks passed; writing began
        bundle.bundle_record(paths.root, out, key_id, piece_size=piece_size)

    sparse_file(paths.files / "big.bin", inside + 20_480)  # now past the limit
    with_manifest(paths)
    with pytest.raises(bundle.TooManyPieces):
        bundle.bundle_record(paths.root, tmp_path / "out2", key_id, piece_size=piece_size)


def make_big_store(tmp_path, models=1000, versions=10):
    root = tmp_path / "bigstore" / "models"
    for number in range(models):
        for version in range(versions):
            folder = root / f"org{number // 50}" / f"model{number}" / "commits" / f"{version:040x}"
            folder.mkdir(parents=True)
            (folder / "summary.json").write_text(
                json.dumps(
                    {
                        "captured_at": "2026-01-01T00:00:00Z",
                        "size_bytes": 1000,
                        "license": {"name": "mit"},
                    }
                )
            )
    return tmp_path / "bigstore"


def test_listing_ten_thousand_versions_takes_under_five_seconds(tmp_path):
    big = make_big_store(tmp_path)
    started = time.monotonic()
    items = store.list_models(big)
    elapsed = time.monotonic() - started
    assert len(items) == 10_000
    assert elapsed < 5.0, f"listing took {elapsed:.1f} s"


def test_working_on_one_bundle_never_looks_at_the_rest_of_the_store(
    bundle_dir, tmp_path, monkeypatch
):
    big = make_big_store(tmp_path, models=200, versions=5)

    def forbidden(*args, **kwargs):
        raise AssertionError("the whole store was scanned")

    monkeypatch.setattr(store, "list_models", forbidden)
    started = time.monotonic()
    verify.verify_bundle([bundle_dir])
    unpack.unpack_bundle([bundle_dir], big)
    assert time.monotonic() - started < 2.0
