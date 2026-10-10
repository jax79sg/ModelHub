"""Targeted regressions: a hostile archive, even one with a valid signature, must never write
outside the store, create links, or add files the manifest does not list (NFR2.10)."""

import hashlib
import io
import json
import tarfile

import pytest

from modelhub import bundle, fsutil, record, signing, unpack

COMMIT = "e" * 40


def regular(name, data):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    return info, data


def link(name, target, hard=False):
    info = tarfile.TarInfo(name)
    info.type = tarfile.LNKTYPE if hard else tarfile.SYMTYPE
    info.linkname = target
    return info, None


def c1_manifest(files):
    entries = [
        {
            "path": path,
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "hub_sha256": None,
            "hub_oid": None,
            "scan": None,
        }
        for path, data in files.items()
    ]
    return record.new_manifest("org/evil", COMMIT, "main", entries, "2026-01-01T00:00:00Z")


def forge(tmp_path, key_id, entries, files=None, declared_stream_size=None):
    """A bundle that is validly signed but whose archive holds exactly `entries`."""
    files = files or {}
    out = tmp_path / "forged"
    out.mkdir(exist_ok=True)
    stem = "org--evil--" + COMMIT[:12]
    c1 = c1_manifest(files)
    c1_bytes = json.dumps(c1, indent=2, sort_keys=True).encode()
    writer = bundle.SliceWriter(stem, lambda index: (out, 4096))
    with tarfile.open(fileobj=writer, mode="w|", format=tarfile.PAX_FORMAT) as tar:
        first = tarfile.TarInfo("manifest.json")
        first.size = len(c1_bytes)
        tar.addfile(first, io.BytesIO(c1_bytes))
        for info, data in entries:
            tar.addfile(info, io.BytesIO(data) if data is not None else None)
    writer.finish()
    doc = bundle._manifest_doc(
        {"model_id": "org/evil", "commit": COMMIT, "captured_at": "2026-01-01T00:00:00Z"},
        hashlib.sha256(c1_bytes).hexdigest(),
        key_id,
        writer,
        4096,
        True,
        "2026-01-01T00:00:00Z",
    )
    if declared_stream_size is not None:
        doc["stream"]["size"] = declared_stream_size
    bundle._write_manifest(out, stem, doc, key_id)
    public = signing.export_public(key_id, tmp_path / "pub.json")
    signing.trust_key(public, public["fingerprint"])
    return out


GOOD = {"a.txt": b"hello"}


def test_a_well_formed_forged_bundle_unpacks(key_id, tmp_path):
    out = forge(tmp_path, key_id, [regular("files/a.txt", b"hello")], GOOD)
    unpack.unpack_bundle([out], tmp_path / "store")
    assert (
        tmp_path / "store/models/org/evil/commits" / COMMIT / "files/a.txt"
    ).read_bytes() == b"hello"


@pytest.mark.parametrize("name", ["../escape.txt", "files/../../escape.txt", "/tmp/absolute.txt"])
def test_an_entry_that_would_leave_the_folder_is_refused(key_id, tmp_path, name):
    out = forge(tmp_path, key_id, [regular(name, b"x")], GOOD)
    with pytest.raises((unpack.UnsafeArchive, fsutil.UnsafePathError)):
        unpack.unpack_bundle([out], tmp_path / "store")
    assert not (tmp_path / "escape.txt").exists()
    assert not list(tmp_path.rglob("absolute.txt"))


def test_a_symbolic_link_is_refused(key_id, tmp_path):
    out = forge(tmp_path, key_id, [link("files/a.txt", "/etc/passwd")], GOOD)
    with pytest.raises(unpack.UnsafeArchive, match="plain files"):
        unpack.unpack_bundle([out], tmp_path / "store")


def test_a_hard_link_is_refused(key_id, tmp_path):
    out = forge(tmp_path, key_id, [link("files/a.txt", "files/b.txt", hard=True)], GOOD)
    with pytest.raises(unpack.UnsafeArchive, match="plain files"):
        unpack.unpack_bundle([out], tmp_path / "store")


def test_a_file_the_manifest_does_not_list_is_refused(key_id, tmp_path):
    out = forge(
        tmp_path, key_id, [regular("files/a.txt", b"hello"), regular("files/extra.sh", b"x")], GOOD
    )
    with pytest.raises(unpack.UnsafeArchive, match="not listed"):
        unpack.unpack_bundle([out], tmp_path / "store")
    assert not list((tmp_path / "store").rglob("extra.sh"))


def test_a_file_whose_size_differs_from_the_manifest_is_refused(key_id, tmp_path):
    out = forge(tmp_path, key_id, [regular("files/a.txt", b"hello world")], GOOD)
    with pytest.raises(unpack.UnsafeArchive, match="not listed"):
        unpack.unpack_bundle([out], tmp_path / "store")


def test_an_unexpected_top_level_entry_is_refused(key_id, tmp_path):
    out = forge(tmp_path, key_id, [regular("files/a.txt", b"hello"), regular("run.sh", b"x")], GOOD)
    with pytest.raises(unpack.UnsafeArchive, match="unexpected"):
        unpack.unpack_bundle([out], tmp_path / "store")


def test_output_may_not_exceed_what_the_signed_manifest_declares(key_id, tmp_path):
    out = forge(
        tmp_path, key_id, [regular("files/a.txt", b"hello")], GOOD, declared_stream_size=600
    )
    with pytest.raises((unpack.UnsafeArchive, unpack.IntegrityFailure), match="declare|match"):
        unpack.unpack_bundle([out], tmp_path / "store")
    assert not list((tmp_path / "store").rglob("a.txt"))


def test_an_archive_that_omits_a_listed_file_is_refused(key_id, tmp_path):
    out = forge(tmp_path, key_id, [], GOOD)
    with pytest.raises(unpack.IntegrityFailure, match="missing"):
        unpack.unpack_bundle([out], tmp_path / "store")


def test_nothing_half_unpacked_is_left_after_a_refusal(key_id, tmp_path):
    out = forge(tmp_path, key_id, [regular("files/a.txt", b"hello"), link("files/b", "/x")], GOOD)
    with pytest.raises(unpack.UnsafeArchive):
        unpack.unpack_bundle([out], tmp_path / "store")
    commits = tmp_path / "store/models/org/evil/commits"
    assert not commits.exists() or list(commits.iterdir()) == []


def test_two_files_differing_only_by_letter_case_are_refused_on_windows(
    key_id, tmp_path, monkeypatch
):
    files = {"A.txt": b"1", "a.txt": b"2"}
    out = forge(
        tmp_path, key_id, [regular("files/A.txt", b"1"), regular("files/a.txt", b"2")], files
    )
    monkeypatch.setattr(fsutil, "IS_WINDOWS", True)
    with pytest.raises(unpack.UnsafeArchive, match="letter case"):
        unpack.unpack_bundle([out], tmp_path / "store")


def test_a_model_name_differing_only_by_case_from_one_in_the_store_is_refused_on_windows(
    key_id, tmp_path, monkeypatch
):
    existing = tmp_path / "store/models/Org/evil/commits"
    existing.mkdir(parents=True)
    out = forge(tmp_path, key_id, [regular("files/a.txt", b"hello")], GOOD)
    monkeypatch.setattr(fsutil, "IS_WINDOWS", True)
    with pytest.raises(unpack.UnsafeArchive, match="letter case"):
        unpack.unpack_bundle([out], tmp_path / "store")
