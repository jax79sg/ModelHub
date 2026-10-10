import json
import os

import pytest
from conftest import COMMIT

from modelhub import bundle, fsutil, pieces


def bundle_to(pulled, key_id, out, piece_size=4096, **kwargs):
    return bundle.bundle_record(pulled, out, key_id, piece_size=piece_size, **kwargs)


def piece_files(out):
    return sorted(p for p in out.glob("*.part-*") if not p.name.startswith("."))


def test_every_piece_is_within_the_size_and_together_they_are_the_whole(pulled, key_id, tmp_path):
    out = tmp_path / "out"
    result = bundle_to(pulled, key_id, out, piece_size=4096)
    files = piece_files(out)
    assert len(files) == len(result.pieces) > 3
    assert all(f.stat().st_size <= 4096 for f in files)
    assert sum(f.stat().st_size for f in files) == result.stream_size
    assert result.stream_size == bundle.tar_stream_size(bundle.record_members(pulled))


def test_the_manifest_records_each_piece_and_the_whole_stream(pulled, key_id, tmp_path):
    out = tmp_path / "out"
    result = bundle_to(pulled, key_id, out)
    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["complete"] is True
    assert manifest["model"] == {
        "id": "org/tiny",
        "commit": COMMIT,
        "captured_at": manifest["model"]["captured_at"],
    }
    offsets = [p["offset"] for p in manifest["pieces"]]
    assert offsets == sorted(offsets) and offsets[0] == 0
    for piece in manifest["pieces"]:
        assert fsutil.sha256_file(out / piece["name"]) == piece["sha256"]
    assert manifest["stream"]["size"] == result.stream_size
    assert manifest["c1_manifest_sha256"] == fsutil.sha256_file(pulled / "manifest.json")


def test_a_piece_size_below_one_gigabyte_is_accepted(pulled, key_id, tmp_path):
    result = bundle_to(pulled, key_id, tmp_path / "out", piece_size=pieces.MIN_PIECE_SIZE)
    assert len(result.pieces) > 10


def test_a_piece_size_below_the_minimum_is_refused(pulled, key_id, tmp_path):
    with pytest.raises(ValueError, match="at least"):
        bundle_to(pulled, key_id, tmp_path / "out", piece_size=pieces.MIN_PIECE_SIZE - 1)
    assert not (tmp_path / "out").exists()


def test_a_stopped_write_leaves_earlier_pieces_alone_and_no_half_piece(
    pulled, key_id, tmp_path, monkeypatch
):
    out = tmp_path / "out"
    real_replace = os.replace

    def failing_replace(source, target):
        if str(target).endswith(".part-000003"):
            raise OSError("drive removed")
        return real_replace(source, target)

    monkeypatch.setattr(fsutil.os, "replace", failing_replace)
    with pytest.raises(OSError, match="drive removed"):
        bundle_to(pulled, key_id, out)
    names = sorted(p.name for p in out.iterdir())
    assert any(n.endswith(".part-000001") for n in names)
    assert any(n.endswith(".part-000002") for n in names)
    assert not any(n.endswith(".part-000003") for n in names)
    assert not any(n.endswith(".partial") for n in names)  # nothing half-written looks finished
    assert not any(
        n.endswith(".bundle.json") for n in names
    )  # no manifest for an unfinished bundle


def test_a_restart_does_not_rewrite_pieces_already_written(pulled, key_id, tmp_path, monkeypatch):
    out = tmp_path / "out"
    real_replace = os.replace

    def failing_replace(source, target):
        if str(target).endswith(".part-000004"):
            raise OSError("drive removed")
        return real_replace(source, target)

    monkeypatch.setattr(fsutil.os, "replace", failing_replace)
    with pytest.raises(OSError):
        bundle_to(pulled, key_id, out)
    first_three = {p.name: p.stat().st_mtime_ns for p in piece_files(out)}
    monkeypatch.setattr(fsutil.os, "replace", real_replace)
    result = bundle_to(pulled, key_id, out)
    for name, mtime in first_three.items():
        assert (out / name).stat().st_mtime_ns == mtime  # not rewritten (NFR3.3)
    assert result.manifest_path.is_file()


def test_not_enough_free_space_writes_nothing_and_says_how_much_is_needed(
    pulled, key_id, tmp_path, monkeypatch
):
    monkeypatch.setattr(fsutil, "free_bytes", lambda path: 10)
    with pytest.raises(bundle.InsufficientSpace, match="bytes needed"):
        bundle_to(pulled, key_id, tmp_path / "out")
    assert piece_files(tmp_path / "out") == []


def test_more_pieces_than_the_numbering_allows_is_refused_before_writing(
    pulled, key_id, tmp_path, monkeypatch
):
    monkeypatch.setattr(pieces, "MAX_PIECES", 3)
    with pytest.raises(bundle.TooManyPieces):
        bundle_to(pulled, key_id, tmp_path / "out", piece_size=pieces.MIN_PIECE_SIZE)
    assert not (tmp_path / "out").exists() or piece_files(tmp_path / "out") == []


def test_a_changed_file_is_caught_so_what_was_scanned_is_what_is_packed(pulled, key_id, tmp_path):
    (pulled / "files" / "config.json").write_bytes(b'{"tampered": true}')
    with pytest.raises(bundle.RecordChanged) as error:
        bundle_to(pulled, key_id, tmp_path / "out")
    assert "changed: config.json" in error.value.problems
    assert piece_files(tmp_path / "out") == []


def test_an_extra_file_is_caught(pulled, key_id, tmp_path):
    (pulled / "files" / "extra.bin").write_bytes(b"new")
    with pytest.raises(bundle.RecordChanged) as error:
        bundle_to(pulled, key_id, tmp_path / "out")
    assert "not in manifest: extra.bin" in error.value.problems


def test_a_missing_file_is_caught(pulled, key_id, tmp_path):
    (pulled / "files" / "config.json").unlink()
    with pytest.raises(bundle.RecordChanged) as error:
        bundle_to(pulled, key_id, tmp_path / "out")
    assert "missing: config.json" in error.value.problems


def test_the_plan_states_the_size_and_piece_count_before_writing(pulled):
    stream_size, count = bundle.plan_bundle(pulled, 4096)
    assert stream_size == bundle.tar_stream_size(bundle.record_members(pulled))
    assert count == -(-stream_size // 4096)
