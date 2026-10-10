"""Text handling that must hold on both systems (NFR7.4, NFR7.5): byte-order marks, Windows line
endings, odd bytes, non-English and long file names."""

import json
import sys

from conftest import COMMIT, FakeHub

from modelhub import bundle, pull, record, signing, unpack

BOM = b"\xef\xbb\xbf"


def pulled_with(tmp_path, files):
    hub = FakeHub()
    hub.add_model("org/tiny", files)
    return pull.pull_model(hub, "org/tiny", tmp_path / "work", selection={"all"}).record_dir


def test_a_readme_with_a_byte_order_mark_and_windows_line_endings_is_kept_exactly(
    tmp_path, picture_server
):
    picture_server.routes["/a.png"] = (200, b"png-bytes", 0)
    readme = BOM + f"# T\r\n![x]({picture_server.base}/a.png)\r\ntext\r\n".encode()
    root = pulled_with(tmp_path, {"README.md": readme})
    assert (root / "files" / "README.md").read_bytes() == readme  # the original: untouched
    local = (root / "readme" / "README.local.md").read_bytes()
    assert local.startswith(BOM) and b"\r\n" in local and b"\n" not in local.replace(b"\r\n", b"")


def test_a_readme_with_bytes_that_are_not_utf8_comes_through_unchanged(tmp_path):
    readme = b"caf\xe9 \xff\xfe odd bytes\n"
    root = pulled_with(tmp_path, {"README.md": readme})
    assert (root / "readme" / "README.local.md").read_bytes() == readme


def test_every_file_the_tool_writes_is_utf8_without_a_mark_and_with_plain_newlines(tmp_path):
    root = pulled_with(tmp_path, {"README.md": "ünïcode — ok".encode(), "w.safetensors": b"w" * 10})
    for name in ("manifest.json", "summary.json", "raw/model_info.json", "raw/tree.json"):
        data = (root / name).read_bytes()
        assert not data.startswith(BOM), name
        assert b"\r\n" not in data, name
        json.loads(data.decode("utf-8"))


def test_a_manifest_saved_with_a_byte_order_mark_is_still_read(tmp_path):
    paths = record.RecordPaths(tmp_path, "org/name", "b" * 40)
    manifest = record.new_manifest("org/name", "b" * 40, "main", [], "2026-01-01T00:00:00Z")
    paths.root.mkdir(parents=True)
    paths.manifest.write_bytes(BOM + json.dumps(manifest).encode())
    assert record.load_manifest(paths.manifest)["commit"] == "b" * 40


AWKWARD = {
    "README.md": b"r",
    "ünï/日本語.txt": "naïve — 日本語".encode(),
    "with space.json": b"{}",
    # a double quote cannot be in a Windows file name
    ("quote'single.txt" if sys.platform == "win32" else "quote\"and'single.txt"): b"q",
    "a/" * 40 + "deep-name-" + "x" * 60 + ".json": b"long",  # over 100 characters in all
}


def test_unusual_file_names_make_the_whole_round_trip_unchanged(tmp_path, key_id):
    root = pulled_with(tmp_path, AWKWARD)
    out = tmp_path / "bundle"
    bundle.bundle_record(root, out, key_id, piece_size=2048)
    doc = signing.export_public(key_id, tmp_path / "p.json")
    signing.trust_key(doc, doc["fingerprint"])
    unpack.unpack_bundle([out], tmp_path / "store")
    rebuilt = tmp_path / "store/models/org/tiny/commits" / COMMIT / "files"
    for name, data in AWKWARD.items():
        assert (rebuilt / name).read_bytes() == data, name
    summary = json.loads((rebuilt.parent / "summary.json").read_text(encoding="utf-8"))
    assert {f["path"] for f in summary["files"]} == set(AWKWARD)
