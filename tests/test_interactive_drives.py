import json

import pytest

from modelhub import bundle, verify


class Drives:
    """Hands out drives the way the command line would, and remembers what was asked."""

    def __init__(self, tmp_path, usable):
        self.tmp_path = tmp_path
        self.usable = usable  # bytes of real space for pieces on each drive
        self.asked = []

    def __call__(self, index):
        self.asked.append(index)
        folder = self.tmp_path / f"drive{index}"
        return folder, bundle.RESERVE + self.usable


def test_each_drive_is_filled_in_turn_and_asked_for_when_needed(pulled, key_id, tmp_path):
    drives = Drives(tmp_path, usable=16_384)
    result = bundle.bundle_record(pulled, tmp_path / "unused", key_id, next_drive=drives)
    assert drives.asked == list(range(1, len(result.pieces) + 1))
    assert len(result.pieces) >= 3
    for index, piece in enumerate(result.pieces, start=1):
        assert (tmp_path / f"drive{index}" / piece["name"]).is_file()
        assert piece["size"] <= 16_384


def test_every_drive_carries_a_manifest_and_only_the_last_is_final(pulled, key_id, tmp_path):
    drives = Drives(tmp_path, usable=16_384)
    result = bundle.bundle_record(pulled, tmp_path / "unused", key_id, next_drive=drives)
    last = len(result.pieces)
    for index in range(1, last + 1):
        manifests = list((tmp_path / f"drive{index}").glob("*.bundle.json"))
        assert len(manifests) == 1
        assert (tmp_path / f"drive{index}" / manifests[0].name.replace(".json", ".sig")).is_file()
        complete = json.loads(manifests[0].read_text())["complete"]
        assert complete is (index == last)


def test_pieces_from_all_the_drives_verify_together_in_any_order(pulled, key_id, tmp_path, home):
    from modelhub import signing

    drives = Drives(tmp_path, usable=16_384)
    result = bundle.bundle_record(pulled, tmp_path / "unused", key_id, next_drive=drives)
    pub = tmp_path / "pub.json"
    doc = signing.export_public(key_id, pub)
    signing.trust_key(doc, doc["fingerprint"])
    folders = [tmp_path / f"drive{i}" for i in range(len(result.pieces), 0, -1)]  # reversed
    reports = verify.verify_bundle(folders)
    assert [r.ok for r in reports] == [True], [p.message for r in reports for p in r.problems]


def test_a_single_drive_alone_is_reported_as_incomplete(pulled, key_id, tmp_path, home):
    drives = Drives(tmp_path, usable=16_384)
    bundle.bundle_record(pulled, tmp_path / "unused", key_id, next_drive=drives)
    reports = verify.verify_bundle([tmp_path / "drive1"])
    assert not reports[0].ok
    assert any(p.code == "incomplete-bundle" for p in reports[0].problems)


def test_a_drive_too_small_for_a_piece_is_refused(pulled, key_id, tmp_path):
    def tiny_drive(index):
        return tmp_path / "d", bundle.RESERVE

    with pytest.raises(bundle.InsufficientSpace, match="too small"):
        bundle.bundle_record(pulled, tmp_path / "unused", key_id, next_drive=tiny_drive)


def test_either_a_piece_size_or_a_drive_callback_is_needed_never_both(pulled, key_id, tmp_path):
    with pytest.raises(ValueError, match="either"):
        bundle.bundle_record(pulled, tmp_path / "o", key_id)
    with pytest.raises(ValueError, match="either"):
        bundle.bundle_record(
            pulled, tmp_path / "o", key_id, piece_size=4096, next_drive=lambda i: (tmp_path, 1)
        )
