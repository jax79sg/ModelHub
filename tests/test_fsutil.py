import hashlib

import pytest

from modelhub import fsutil


def test_sha256_file_matches_hashlib_with_small_blocks(tmp_path):
    data = bytes(range(256)) * 4000
    path = tmp_path / "big.bin"
    path.write_bytes(data)
    assert fsutil.sha256_file(path, block=1000) == hashlib.sha256(data).hexdigest()


def test_atomic_write_replaces_existing_file(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("old")
    fsutil.atomic_write_text(path, "new")
    assert path.read_text() == "new"


def test_atomic_write_leaves_no_partial_file_when_it_fails(tmp_path, monkeypatch):
    path = tmp_path / "a.txt"
    path.write_text("old")

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(fsutil.os, "replace", boom)
    with pytest.raises(OSError):
        fsutil.atomic_write_text(path, "new")
    assert path.read_text() == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["a.txt"]


def test_atomic_file_stream_is_invisible_until_finished(tmp_path):
    path = tmp_path / "piece.bin"
    with fsutil.AtomicFile(path) as handle:
        handle.write(b"abc")
        assert not path.exists()
    assert path.read_bytes() == b"abc"


def test_safe_join_accepts_nested_paths(tmp_path):
    assert fsutil.safe_join(tmp_path, "a/b/c.txt") == (tmp_path / "a" / "b" / "c.txt").resolve()


@pytest.mark.parametrize("bad", ["../x", "a/../../x", "/etc/passwd", "C:\\x", "a/\x00b"])
def test_safe_join_rejects_paths_that_escape_the_root(tmp_path, bad):
    with pytest.raises(fsutil.UnsafePathError):
        fsutil.safe_join(tmp_path, bad)


def test_git_blob_sha1_matches_git_definition(tmp_path):
    path = tmp_path / "f"
    path.write_bytes(b"hello\n")
    assert fsutil.git_blob_sha1(path) == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_safe_join_does_not_depend_on_how_the_system_spells_the_target(tmp_path, monkeypatch):
    # Found on Windows: while several files were being written at once, resolving a new file's
    # path sometimes gave the old short spelling of the folder (RUNNER~1) and a plain
    # "config.json" was refused as escaping its folder.
    real = fsutil.Path.resolve

    def spelled_differently(self, *args, **kwargs):
        resolved = real(self, *args, **kwargs)
        if resolved.name == "config.json":
            return resolved.parent.parent / "SHORT~1" / "config.json"
        return resolved

    monkeypatch.setattr(fsutil.Path, "resolve", spelled_differently)
    assert fsutil.safe_join(tmp_path, "config.json").name == "config.json"


def test_safe_join_refuses_a_link_inside_the_folder_that_leads_outside(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    inside = tmp_path / "root"
    inside.mkdir()
    try:
        (inside / "link").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("this system does not allow making links")
    with pytest.raises(fsutil.UnsafePathError):
        fsutil.safe_join(inside, "link/stolen.txt")
