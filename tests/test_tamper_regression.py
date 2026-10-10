"""The targeted regression for tampering (NFR2.1 to NFR2.4): a change of one byte anywhere,
a missing or replaced signature, or an unknown signer must always be caught, and nothing may
be rebuilt from such a bundle."""

import base64
import json
import shutil

import pytest
from conftest import COMMIT

from modelhub import bundle, signing, unpack, verify


def flip_one_byte(path, offset=0):
    data = bytearray(path.read_bytes())
    data[offset] ^= 0x01
    path.write_bytes(bytes(data))


def codes(bundle_dir):
    return {p.code for r in verify.verify_bundle([bundle_dir]) for p in r.problems}


def test_a_change_of_one_byte_in_any_piece_is_caught(bundle_dir, tmp_path):
    for piece in sorted(bundle_dir.glob("*.part-*")):
        backup = tmp_path / "backup"
        shutil.copy(piece, backup)
        for offset in (0, piece.stat().st_size // 2, piece.stat().st_size - 1):
            flip_one_byte(piece, offset)
            assert codes(bundle_dir) == {"piece-damaged"}, (piece.name, offset)
            shutil.copy(backup, piece)
    assert codes(bundle_dir) == set()  # everything restored, so the bundle is good again


def test_a_change_of_one_byte_in_the_manifest_breaks_the_signature(bundle_dir):
    manifest = next(bundle_dir.glob("*.bundle.json"))
    original = manifest.read_bytes()
    for offset in range(0, len(original), max(1, len(original) // 40)):
        data = bytearray(original)
        data[offset] ^= 0x01
        manifest.write_bytes(bytes(data))
        found = codes(bundle_dir)
        assert found, f"a change at byte {offset} of the manifest was not noticed"
    manifest.write_bytes(original)
    assert codes(bundle_dir) == set()


def test_a_manifest_edited_to_match_a_swapped_piece_still_fails_its_signature(bundle_dir):
    manifest = next(bundle_dir.glob("*.bundle.json"))
    doc = json.loads(manifest.read_text())
    piece = doc["pieces"][2]
    path = bundle_dir / piece["name"]
    flip_one_byte(path)
    from modelhub import fsutil

    piece["sha256"] = fsutil.sha256_file(path)  # the attacker updates the checksum too
    manifest.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    assert codes(bundle_dir) == {"signature-invalid"}


def test_a_change_in_the_signature_file_is_caught(bundle_dir):
    sig_path = next(bundle_dir.glob("*.bundle.sig"))
    doc = json.loads(sig_path.read_text())
    raw = bytearray(base64.b64decode(doc["signature"]))
    raw[0] ^= 0x01
    doc["signature"] = base64.b64encode(bytes(raw)).decode()
    sig_path.write_text(json.dumps(doc))
    assert codes(bundle_dir) == {"signature-invalid"}


def test_a_bundle_with_no_signature_file_is_refused(bundle_dir):
    next(bundle_dir.glob("*.bundle.sig")).unlink()
    assert codes(bundle_dir) == {"signature-missing"}


def test_an_unreadable_signature_file_counts_as_missing_or_invalid(bundle_dir):
    next(bundle_dir.glob("*.bundle.sig")).write_text("not json at all")
    assert codes(bundle_dir) & {"signature-missing", "signature-invalid", "key-untrusted"}


def test_a_bundle_signed_by_a_stranger_is_refused(pulled, home, tmp_path):
    stranger = signing.create_key("stranger")
    out = tmp_path / "stranger-bundle"
    bundle.bundle_record(pulled, out, stranger["key_id"], piece_size=8192)
    assert codes(out) == {"key-untrusted"}


def test_pieces_swapped_with_each_other_are_caught(bundle_dir):
    files = sorted(bundle_dir.glob("*.part-*"))
    first, second = files[0], files[1]
    tmp = bundle_dir / "swap"
    first.rename(tmp)
    second.rename(first)
    tmp.rename(second)
    assert codes(bundle_dir) == {"piece-damaged"}


def test_a_truncated_last_piece_is_caught(bundle_dir):
    last = max(bundle_dir.glob("*.part-*"))
    last.write_bytes(last.read_bytes()[:-1])
    assert codes(bundle_dir) == {"piece-damaged"}


@pytest.mark.parametrize("damage", ["flip", "remove-signature", "truncate"])
def test_nothing_is_rebuilt_from_a_tampered_bundle(bundle_dir, tmp_path, damage):
    first = min(bundle_dir.glob("*.part-*"))
    if damage == "flip":
        flip_one_byte(first, 5)
    elif damage == "remove-signature":
        next(bundle_dir.glob("*.bundle.sig")).unlink()
    else:
        first.write_bytes(first.read_bytes()[:-3])
    with pytest.raises(verify.VerifyFailed):
        unpack.unpack_bundle([bundle_dir], tmp_path / "store")
    assert not (tmp_path / "store").exists()


def test_a_file_changed_in_the_store_after_unpacking_is_caught(bundle_dir, tmp_path):
    unpack.unpack_bundle([bundle_dir], tmp_path / "store")
    files_dir = tmp_path / "store" / "models/org/tiny/commits" / COMMIT / "files"
    for target in sorted(p for p in files_dir.rglob("*") if p.is_file()):
        backup = tmp_path / "keep"
        shutil.copy(target, backup)
        flip_one_byte(target, 0)
        problems = verify.verify_store(tmp_path / "store")
        assert [p.code for p in problems] == ["file-damaged"], target.name
        shutil.copy(backup, target)
    assert verify.verify_store(tmp_path / "store") == []
