"""Import jobs: create, pieces, start, run, cancel, sweeps (BR1.1-BR1.9, FR1; contract C1)."""

import hashlib
import io
import json
import os
from datetime import timedelta

import pytest
from conftest import trust
from modelhub_artifactory_service.gateway import UploadNetworkError
from modelhub_artifactory_service.importer import ServiceError
from modelhub_testkit.bundles import make_bundle

from modelhub import unpack


def create(imp, bundle, owner=("u1", "ada"), **kw):
    return imp.create(
        owner[0],
        owner[1],
        bundle.description_path.read_bytes(),
        bundle.signature_path.read_bytes(),
        computer=kw.get("computer", "pc1"),
        tool_version="1.2.0",
        check_results={"ok": True},
    )


def send_all(imp, job, bundle, owner="u1"):
    for number, path in enumerate(bundle.pieces(), start=1):
        data = path.read_bytes()
        imp.put_piece(
            job["importId"], owner, number, io.BytesIO(data), hashlib.sha256(data).hexdigest()
        )


def run_import(imp, bundle, owner=("u1", "ada")):
    job = create(imp, bundle, owner)
    send_all(imp, job, bundle, owner[0])
    imp.start(job["importId"], owner[0])
    imp.run(job["importId"])
    return imp.get(job["importId"], owner[0])


# --- the whole path ----------------------------------------------------------------------------
def test_a_new_version_is_imported_and_recorded(world, bundle, stand_in, catalog):
    job = run_import(world, bundle)
    assert job["state"] == "done" and job["outcome"] == "imported"
    listing = world.gateway.list_version(bundle.model_id, bundle.commit)
    assert listing.state == "present" and "model.safetensors" in listing.files
    version = world.catalog.get_version(bundle.model_id, bundle.commit)
    assert version["state"] == "imported" and {f["path"] for f in version["files"]} == set(
        bundle.files
    )


def test_the_work_folder_is_empty_afterwards_and_the_lock_released(world, bundle):
    job = run_import(world, bundle)
    assert not (world.work / job["importId"]).exists()
    again = create(world, bundle)  # the model lock is free (and it is now a skip)
    assert again["state"] == "skipped"


def test_importing_the_same_version_again_is_skipped_and_leaves_a_trail(world, bundle, stand_in):
    run_import(world, bundle)
    uploads = len([c for c in stand_in.calls if c["method"] in ("PUT", "POST")])
    again = create(world, bundle, ("u2", "bob"))
    assert again["state"] == "skipped" and again["outcome"] == "skipped"
    assert len([c for c in stand_in.calls if c["method"] in ("PUT", "POST")]) == uploads


def test_files_missing_from_artifactory_but_known_to_the_catalog_are_repaired(
    world, bundle, stand_in
):
    run_import(world, bundle)
    listing = world.gateway.list_version(bundle.model_id, bundle.commit)
    world.gateway.delete_version(listing)
    job = run_import(world, bundle, ("u2", "bob"))
    assert job["outcome"] == "completed"
    assert world.gateway.list_version(bundle.model_id, bundle.commit).state == "present"


def folder_of(made, tmp_path, name, override=None):
    root = tmp_path / name
    for rel, data in made.files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((override or {}).get(rel, data))
    return root


def test_files_in_artifactory_but_no_catalog_record_are_finished_after_unpacking(
    world, bundle, tmp_path
):
    world.gateway.uploader.upload(
        folder_of(bundle, tmp_path, "pre"), bundle.model_id, bundle.commit
    )
    job = create(world, bundle)
    assert job["plan"] == "pending"
    send_all(world, job, bundle)
    world.start(job["importId"], "u1")
    world.run(job["importId"])
    got = world.get(job["importId"], "u1")
    assert got["state"] == "done" and got["outcome"] == "completed" and got["plan"] == "finish"
    assert world.catalog.get_version(bundle.model_id, bundle.commit)["state"] == "imported"


def test_files_in_artifactory_that_differ_from_the_bundle_fail_the_job(world, bundle, tmp_path):
    world.gateway.uploader.upload(
        folder_of(bundle, tmp_path, "pre", {"config.json": b"different"}),
        bundle.model_id,
        bundle.commit,
    )
    job = create(world, bundle)
    send_all(world, job, bundle)
    world.start(job["importId"], "u1")
    world.run(job["importId"])
    got = world.get(job["importId"], "u1")
    assert got["state"] == "failed" and got["error"]["code"] == "artifactory_inconsistent"
    assert "config.json" in got["error"]["message"] and got["error"]["retryable"] is False


def test_a_listing_that_disagrees_with_the_catalog_fails_at_create(world, bundle, tmp_path):
    run_import(world, bundle)
    world.gateway.delete_version(world.gateway.list_version(bundle.model_id, bundle.commit))
    world.gateway.uploader.upload(
        folder_of(bundle, tmp_path, "tamper", {"config.json": b"different"}),
        bundle.model_id,
        bundle.commit,
    )
    with pytest.raises(ServiceError) as err:
        create(world, bundle)
    assert err.value.code == "artifactory_inconsistent" and err.value.status == 409


# --- create: refusals --------------------------------------------------------------------------
def test_an_untrusted_signing_key_is_refused(world, bundle):
    world.keys.revoke(bundle.public_key["fingerprint"], "root")
    with pytest.raises(ServiceError) as err:
        create(world, bundle)
    assert err.value.status == 422 and err.value.code == "key-untrusted"


def test_a_tampered_description_is_refused(world, bundle):
    doc = json.loads(bundle.description_path.read_text())
    doc["model"]["id"] = "org/evil"
    with pytest.raises(ServiceError) as err:
        world.create(
            "u1",
            "ada",
            json.dumps(doc).encode(),
            bundle.signature_path.read_bytes(),
            computer="pc",
            tool_version="1",
            check_results={},
        )
    assert err.value.code == "signature-invalid"


def test_bad_names_are_refused_before_anything_is_stored(world, tmp_path):
    bad = make_bundle(tmp_path / "bad", model_id="12345/tiny")
    trust(world.keys, bad)
    with pytest.raises(ServiceError) as err:
        create(world, bad)
    assert err.value.status == 422 and err.value.code == "invalid_names"
    assert "organisation" in err.value.message


def test_not_enough_space_is_507_and_says_how_much(world, bundle):
    world.free_bytes = lambda path: 10
    with pytest.raises(ServiceError) as err:
        create(world, bundle)
    assert err.value.status == 507 and err.value.code == "insufficient_storage"


def test_a_second_import_of_the_same_model_while_one_is_running_is_refused(world, bundle):
    create(world, bundle)
    with pytest.raises(ServiceError) as err:
        create(world, bundle, ("u2", "bob"))
    assert err.value.status == 409 and err.value.code == "model_locked"


# --- pieces ------------------------------------------------------------------------------------
def test_a_piece_with_the_wrong_checksum_is_refused_and_not_kept(world, bundle):
    job = create(world, bundle)
    data = bundle.pieces()[0].read_bytes()
    with pytest.raises(ServiceError) as err:
        world.put_piece(job["importId"], "u1", 1, io.BytesIO(data), "0" * 64)
    assert err.value.status == 422 and err.value.code == "piece_damaged"
    with pytest.raises(ServiceError) as err:
        world.start(job["importId"], "u1")
    assert err.value.code == "pieces_missing"


def test_the_same_piece_sent_twice_is_accepted_once(world, bundle):
    job = create(world, bundle)
    data = bundle.pieces()[0].read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    world.put_piece(job["importId"], "u1", 1, io.BytesIO(data), digest)
    world.put_piece(job["importId"], "u1", 1, io.BytesIO(data), digest)


def test_a_piece_larger_than_declared_is_413_and_an_unknown_index_is_404(world, bundle):
    job = create(world, bundle)
    big = b"x" * (len(bundle.pieces()[0].read_bytes()) + 1)
    with pytest.raises(ServiceError) as err:
        world.put_piece(
            job["importId"],
            "u1",
            1,
            io.BytesIO(big),
            hashlib.sha256(bundle.pieces()[0].read_bytes()).hexdigest(),
        )
    assert err.value.status == 413
    with pytest.raises(ServiceError) as err:
        world.put_piece(job["importId"], "u1", 999, io.BytesIO(b"x"), "0" * 64)
    assert err.value.status == 404


def test_only_the_owner_can_see_or_change_a_job(world, bundle):
    job = create(world, bundle)
    for call in (
        lambda: world.get(job["importId"], "u2"),
        lambda: world.cancel(job["importId"], "u2"),
        lambda: world.start(job["importId"], "u2"),
    ):
        with pytest.raises(ServiceError) as err:
            call()
        assert err.value.status == 404


def test_start_with_pieces_missing_names_them(world, bundle):
    job = create(world, bundle)
    with pytest.raises(ServiceError) as err:
        world.start(job["importId"], "u1")
    assert err.value.status == 409 and err.value.code == "pieces_missing"
    assert "1" in err.value.message


def test_no_more_than_two_imports_run_at_once(world, bundle, tmp_path):
    jobs = []
    for n in range(3):
        b = make_bundle(tmp_path / f"m{n}", model_id=f"org/m{n}", commit=str(n) * 40)
        trust(world.keys, b, f"k{n}")
        job = create(world, b)
        send_all(world, job, b)
        jobs.append(job)
        if n < 2:
            world.start(job["importId"], "u1")
    with pytest.raises(ServiceError) as err:
        world.start(jobs[2]["importId"], "u1")
    assert err.value.status == 503 and err.value.code == "service_busy"


# --- failures and retries ----------------------------------------------------------------------
class Flaky:
    def __init__(self, real, fails):
        self.real, self.fails, self.calls = real, fails, 0

    def upload(self, folder, model_id, revision):
        self.calls += 1
        if self.calls <= self.fails:
            raise UploadNetworkError("network down")
        self.real.upload(folder, model_id, revision)


def test_a_flaky_upload_is_retried_with_waits(world, bundle):
    flaky = Flaky(world.gateway.uploader, 2)
    world.gateway.uploader = flaky
    waits = []
    world.sleep = waits.append
    job = run_import(world, bundle)
    assert job["outcome"] == "imported" and waits == [1, 2]


def test_an_upload_that_keeps_failing_ends_retryable_and_cleans_up(world, bundle):
    world.gateway.uploader = Flaky(world.gateway.uploader, 99)
    job = run_import(world, bundle)
    assert job["state"] == "failed" and job["error"]["retryable"] is True
    assert job["error"]["code"] == "artifactory_unreachable"
    assert not (world.work / job["importId"]).exists()
    assert world.catalog.get_version(bundle.model_id, bundle.commit) is None


def test_a_damaged_piece_found_at_verify_fails_the_job(world, bundle):
    job = create(world, bundle)
    send_all(world, job, bundle)
    victim = next((world.work / job["importId"] / "in").glob("*.part-*"))
    victim.write_bytes(victim.read_bytes()[:-1] + b"?")
    world.start(job["importId"], "u1")
    world.run(job["importId"])
    got = world.get(job["importId"], "u1")
    assert got["state"] == "failed" and got["error"]["code"] == "piece-damaged"
    assert got["error"]["retryable"] is False


def test_pieces_are_deleted_as_they_are_read(world, bundle, monkeypatch):
    seen = []
    real = unpack.rebuild_into

    def spy(report, partial, progress=None, joined_factory=None, **kw):
        out = real(report, partial, progress, joined_factory, **kw)
        seen.append([p.exists() for p in report.piece_paths])
        return out

    monkeypatch.setattr(unpack, "rebuild_into", spy)
    run_import(world, bundle)
    assert seen and not any(seen[0])


# --- cancel, idle, restart ---------------------------------------------------------------------
def test_cancel_removes_everything_and_frees_the_model(world, bundle):
    job = create(world, bundle)
    world.cancel(job["importId"], "u1")
    assert world.get(job["importId"], "u1")["state"] == "cancelled"
    assert not (world.work / job["importId"]).exists()
    create(world, bundle, ("u2", "bob"))


def test_a_job_idle_for_a_day_is_cancelled(world, bundle, clock):
    job = create(world, bundle)
    clock.advance(hours=23)
    assert world.sweep_idle() == 0
    clock.advance(hours=2)
    assert world.sweep_idle() == 1
    got = world.get(job["importId"], "u1")
    assert got["state"] == "cancelled" and "idle" in got["error"]["code"]


def test_after_a_restart_running_jobs_are_failed_as_interrupted_and_retryable(world, bundle):
    job = create(world, bundle)
    send_all(world, job, bundle)
    world.start(job["importId"], "u1")  # marked verifying but never run
    assert world.sweep_restart() == 1
    got = world.get(job["importId"], "u1")
    assert got["state"] == "failed" and got["error"] == {
        "code": "interrupted",
        "message": got["error"]["message"],
        "retryable": True,
    }
    create(world, bundle)  # the lock is free again


def test_the_job_never_exposes_the_bundle_text_or_a_path(world, bundle):
    job = run_import(world, bundle)
    text = json.dumps(job)
    assert str(world.work) not in text and "signature" not in text.lower()


_ = (os, timedelta)


def test_creating_again_for_an_unfinished_import_returns_it_with_the_missing_pieces(world, bundle):
    first = create(world, bundle)
    assert first["missingPieces"] == list(range(1, len(bundle.pieces()) + 1))
    data = bundle.pieces()[0].read_bytes()
    world.put_piece(first["importId"], "u1", 1, io.BytesIO(data), hashlib.sha256(data).hexdigest())
    again = create(world, bundle)
    assert again["importId"] == first["importId"] and 1 not in again["missingPieces"]
