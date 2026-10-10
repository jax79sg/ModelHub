import tarfile

import pytest

from modelhub import bundle, pieces


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("900MB", 900_000_000),
        ("1.5GB", 1_500_000_000),
        ("4KiB", 4096),
        ("2 MiB", 2 * 1024 * 1024),
        ("500", 500),
        ("1tb", 1_000_000_000_000),
    ],
)
def test_parse_size_reads_drive_style_sizes(text, expected):
    assert pieces.parse_size(text) == expected


@pytest.mark.parametrize("bad", ["", "big", "12XB", "-5MB", "MB"])
def test_parse_size_refuses_nonsense_and_says_why(bad):
    with pytest.raises(ValueError, match="size"):
        pieces.parse_size(bad)


def test_names_follow_the_contract():
    stem = pieces.stem_for("org/name", "abcdef0123456789" + "0" * 24)
    assert stem == "org--name--abcdef012345"
    assert pieces.piece_name(stem, 7) == "org--name--abcdef012345.part-000007"


def test_the_smallest_piece_size_is_documented_and_below_one_gigabyte():
    assert pieces.MIN_PIECE_SIZE < 1_000_000_000
    assert pieces.MAX_PIECES == 999_999


def test_computed_archive_size_matches_the_real_archive(pulled, tmp_path):
    members = bundle.record_members(pulled)
    joined = tmp_path / "x.tar"
    with tarfile.open(joined, "w|", format=tarfile.PAX_FORMAT) as tar, open(joined, "ab"):
        pass
    sink = tmp_path / "real.tar"
    with tarfile.open(sink, "w", format=tarfile.PAX_FORMAT) as tar:
        for arcname, path in members:
            with open(path, "rb") as handle:
                tar.addfile(bundle._tarinfo(arcname, path), handle)
    assert bundle.tar_stream_size(members) == sink.stat().st_size


def test_the_manifest_comes_first_in_the_archive(pulled):
    assert bundle.record_members(pulled)[0][0] == "manifest.json"
