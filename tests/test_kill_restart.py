"""Stop the tool at every moment a file is written, then run it again: the second run must
finish correctly and nothing half-written may be mistaken for finished (NFR3.1)."""

import os

import pytest
from conftest import COMMIT

from modelhub import bundle, pull, signing, store, unpack, verify


class Killed(BaseException):
    """Stands for the power going off: not an ordinary error, so nothing handles it."""


def count_write_points(operation, fresh):
    """How many files a clean run finishes writing (each ends with a rename)."""
    real_replace = os.replace
    counter = {"n": 0}

    def counting(source, target):
        counter["n"] += 1
        return real_replace(source, target)

    state = fresh()
    os.replace = counting
    try:
        operation(state)
    finally:
        os.replace = real_replace
    return counter["n"]


def kill_at_every_write_point(operation, fresh, check):
    """For each write point: start afresh, stop the run there, run again, then check the result."""
    total = count_write_points(operation, fresh)
    real_replace = os.replace
    for point in range(1, total + 1):
        state = fresh()
        counter = {"n": 0}

        def killing(source, target, counter=counter, point=point):
            counter["n"] += 1
            if counter["n"] == point:
                raise Killed
            return real_replace(source, target)

        os.replace = killing
        try:
            with pytest.raises(Killed):
                operation(state)
        finally:
            os.replace = real_replace
        operation(state)  # run again, with nothing in the way
        check(state, point)
    return total


def test_a_pull_stopped_at_any_write_point_finishes_cleanly_when_run_again(fake_hub, tmp_path):
    counter = {"n": 0}

    def fresh():
        counter["n"] += 1
        return tmp_path / f"work{counter['n']}"

    def operation(work):
        pull.pull_model(fake_hub, "org/tiny", work, selection={"all"}, workers=1)

    def check(work, point):
        record_dir = work / "models/org/tiny/commits" / COMMIT
        assert bundle.check_record(record_dir)["commit"] == COMMIT, f"after stopping at {point}"

    assert kill_at_every_write_point(operation, fresh, check) >= 8


def test_a_bundle_stopped_at_any_write_point_finishes_cleanly_when_run_again(
    pulled, key_id, tmp_path
):
    doc = signing.export_public(key_id, tmp_path / "p.json")
    signing.trust_key(doc, doc["fingerprint"])
    counter = {"n": 0}

    def fresh():
        counter["n"] += 1
        return tmp_path / f"out{counter['n']}"

    def operation(out):
        bundle.bundle_record(pulled, out, key_id, piece_size=4096)

    def check(out, point):
        reports = verify.verify_bundle([out])
        assert [r.ok for r in reports] == [True], f"after stopping at {point}"
        # and the finished bundle really rebuilds
        unpack.unpack_bundle([out], out.parent / f"s{out.name}")

    assert kill_at_every_write_point(operation, fresh, check) >= 10


def test_an_unpack_stopped_at_any_write_point_finishes_cleanly_when_run_again(bundle_dir, tmp_path):
    counter = {"n": 0}

    def fresh():
        counter["n"] += 1
        return tmp_path / f"store{counter['n']}"

    def operation(store_dir):
        unpack.unpack_bundle([bundle_dir], store_dir)

    def check(store_dir, point):
        assert verify.verify_store(store_dir) == [], f"after stopping at {point}"
        root = store_dir / "models/org/tiny"
        # the pointers exist too, even when the stop came right after the last rename
        assert (root / "latest").read_text().strip() == COMMIT, f"after stopping at {point}"
        assert (root / "refs/main").read_text().strip() == COMMIT, f"after stopping at {point}"
        [item] = store.list_models(store_dir)
        assert item.latest is True

    assert kill_at_every_write_point(operation, fresh, check) >= 8


def test_the_manifest_is_written_last_so_an_unfinished_bundle_is_never_complete(
    pulled, key_id, tmp_path
):
    out = tmp_path / "out"
    real_replace = os.replace

    def kill_before_the_manifest(source, target):
        if str(target).endswith(".bundle.json"):
            raise Killed
        return real_replace(source, target)

    os.replace = kill_before_the_manifest
    try:
        with pytest.raises(Killed):
            bundle.bundle_record(pulled, out, key_id, piece_size=4096)
    finally:
        os.replace = real_replace
    assert not list(out.glob("*.bundle.json"))
    assert list(out.glob("*.part-*"))  # the pieces are there, but nothing vouches for them yet
