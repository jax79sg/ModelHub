import json

import pytest

from modelhub import record

COMMIT = "b" * 40


def test_record_paths_follow_the_contract_layout(tmp_path):
    paths = record.RecordPaths(tmp_path, "org/name", COMMIT)
    assert paths.root == tmp_path / "models" / "org" / "name" / "commits" / COMMIT
    assert paths.files == paths.root / "files"
    assert paths.raw == paths.root / "raw"
    assert paths.manifest == paths.root / "manifest.json"
    assert paths.summary == paths.root / "summary.json"


def test_build_manifest_hashes_every_file(tmp_path):
    files = tmp_path / "files"
    files.mkdir()
    (files / "a.txt").write_bytes(b"hello")
    (files / "sub").mkdir()
    (files / "sub" / "b.txt").write_bytes(b"world!")
    entries = record.build_file_entries(files, hub_info={})
    by_path = {e["path"]: e for e in entries}
    assert set(by_path) == {"a.txt", "sub/b.txt"}
    assert by_path["a.txt"]["size"] == 5
    assert (
        by_path["a.txt"]["sha256"]
        == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )
    assert by_path["sub/b.txt"]["hub_sha256"] is None


def test_manifest_round_trips_through_disk(tmp_path):
    paths = record.RecordPaths(tmp_path, "org/name", COMMIT)
    manifest = record.new_manifest(
        "org/name", COMMIT, "main", [], captured_at="2026-01-01T00:00:00Z"
    )
    record.write_manifest(paths, manifest)
    assert record.load_manifest(paths.manifest) == manifest
    assert manifest["format_version"] == record.FORMAT_VERSION


def test_manifest_with_newer_major_version_is_refused(tmp_path):
    paths = record.RecordPaths(tmp_path, "org/name", COMMIT)
    manifest = record.new_manifest(
        "org/name", COMMIT, "main", [], captured_at="2026-01-01T00:00:00Z"
    )
    manifest["format_version"] = "99.0"
    paths.root.mkdir(parents=True)
    paths.manifest.write_text(json.dumps(manifest))
    with pytest.raises(record.UnsupportedFormat):
        record.load_manifest(paths.manifest)


def test_manifest_with_older_or_same_major_and_unknown_fields_is_read(tmp_path):
    paths = record.RecordPaths(tmp_path, "org/name", COMMIT)
    manifest = record.new_manifest(
        "org/name", COMMIT, "main", [], captured_at="2026-01-01T00:00:00Z"
    )
    manifest["field_added_later"] = {"x": 1}
    paths.root.mkdir(parents=True)
    paths.manifest.write_text(json.dumps(manifest))
    assert record.load_manifest(paths.manifest)["field_added_later"] == {"x": 1}
