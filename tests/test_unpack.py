import json
import os

import pytest
from conftest import COMMIT, TINY_FILES
from typer.testing import CliRunner

from modelhub import bundle, cli, fsutil, pull, signing, unpack, verify

runner = CliRunner()


def rebuilt(tmp_path):
    return tmp_path / "store" / "models" / "org" / "tiny"


def test_unpack_rebuilds_the_store_layout(bundle_dir, tmp_path):
    results = unpack.unpack_bundle([bundle_dir], tmp_path / "store")
    assert [r.already_present for r in results] == [False]
    root = rebuilt(tmp_path)
    for name, data in TINY_FILES.items():
        assert (root / "commits" / COMMIT / "files" / name).read_bytes() == data
    assert (root / "commits" / COMMIT / "summary.json").is_file()
    assert (root / "latest").read_text().strip() == COMMIT
    assert (root / "refs" / "main").read_text().strip() == COMMIT


def test_unpacking_the_same_bundle_again_changes_nothing(bundle_dir, tmp_path):
    unpack.unpack_bundle([bundle_dir], tmp_path / "store")
    results = unpack.unpack_bundle([bundle_dir], tmp_path / "store")
    assert results[0].already_present is True


def test_a_named_version_gets_a_ref_but_does_not_move_latest(fake_hub, key_id, tmp_path):
    record = pull.pull_model(
        fake_hub, "org/tiny", tmp_path / "w", revision="v1.0", selection={"all"}
    ).record_dir
    out = tmp_path / "b"
    bundle.bundle_record(record, out, key_id, piece_size=8192)
    doc = signing.export_public(key_id, tmp_path / "p.json")
    signing.trust_key(doc, doc["fingerprint"])
    unpack.unpack_bundle([out], tmp_path / "store")
    root = rebuilt(tmp_path)
    assert (root / "refs" / "v1.0").read_text().strip() == COMMIT
    assert not (root / "latest").exists()


def test_a_bad_bundle_is_refused_before_anything_is_written(bundle_dir, tmp_path):
    next(iter(sorted(bundle_dir.glob("*.part-000002")))).write_bytes(b"damaged")
    with pytest.raises(verify.VerifyFailed):
        unpack.unpack_bundle([bundle_dir], tmp_path / "store")
    assert not (tmp_path / "store").exists()


def test_a_rebuilt_file_that_fails_its_checksum_is_not_left_behind(
    pulled, key_id, tmp_path, monkeypatch
):
    manifest = json.loads((pulled / "manifest.json").read_text())
    next(f for f in manifest["files"] if f["path"] == "config.json")["sha256"] = "0" * 64
    (pulled / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(bundle, "check_record", lambda root: manifest)  # a lying signer
    out = tmp_path / "b"
    bundle.bundle_record(pulled, out, key_id, piece_size=8192)
    doc = signing.export_public(key_id, tmp_path / "p.json")
    signing.trust_key(doc, doc["fingerprint"])
    with pytest.raises(unpack.IntegrityFailure, match="config.json"):
        unpack.unpack_bundle([out], tmp_path / "store")
    assert not list((tmp_path / "store").rglob("config.json"))
    assert not (rebuilt(tmp_path) / "commits" / COMMIT).exists()


def test_a_stopped_rebuild_continues_without_rewriting_finished_files(
    bundle_dir, tmp_path, monkeypatch
):
    real = unpack._write_member
    calls = {"n": 0}

    def stop_after_three(tar, member, partial, expected):
        calls["n"] += 1
        if calls["n"] == 4:
            raise OSError("power cut")
        return real(tar, member, partial, expected)

    monkeypatch.setattr(unpack, "_write_member", stop_after_three)
    with pytest.raises(OSError, match="power cut"):
        unpack.unpack_bundle([bundle_dir], tmp_path / "store")
    partial = rebuilt(tmp_path) / "commits" / f".{COMMIT}.partial"
    finished = {p: p.stat().st_mtime_ns for p in partial.rglob("*") if p.is_file()}
    assert finished
    monkeypatch.setattr(unpack, "_write_member", real)
    unpack.unpack_bundle([bundle_dir], tmp_path / "store")
    for path, mtime in finished.items():
        final = rebuilt(tmp_path) / "commits" / COMMIT / path.relative_to(partial)
        assert final.stat().st_mtime_ns == mtime  # not rewritten (NFR3.4)
    assert not partial.exists()


def test_two_runs_on_one_model_at_once_are_not_allowed(bundle_dir, tmp_path):
    with fsutil.RunLock(rebuilt(tmp_path)), pytest.raises(fsutil.LockedError):
        unpack.unpack_bundle([bundle_dir], tmp_path / "store")


@pytest.fixture
def run(home):
    def _run(*args):
        return runner.invoke(cli.app, [str(a) for a in args], env={"MODELHUB_HOME": str(home)})

    return _run


def test_cli_unpack_ends_zero_and_says_where(run, bundle_dir, tmp_path):
    result = run("unpack", bundle_dir, "--store", tmp_path / "store")
    assert result.exit_code == 0, result.output
    assert "org/tiny" in result.output


def test_cli_unpack_of_a_damaged_bundle_ends_one_and_names_the_piece(run, bundle_dir, tmp_path):
    victim = next(iter(sorted(bundle_dir.glob("*.part-000003"))))
    victim.unlink()
    result = run("unpack", bundle_dir, "--store", tmp_path / "store")
    assert result.exit_code == 1
    assert victim.name in result.output


def test_cli_unpack_reports_a_folder_in_use_with_status_2(run, bundle_dir, tmp_path):
    with fsutil.RunLock(rebuilt(tmp_path)):
        result = run("unpack", bundle_dir, "--store", tmp_path / "store")
    assert result.exit_code == 2
    assert "another run" in result.output


def test_the_default_check_is_all_files_present(bundle_dir, tmp_path):
    unpack.unpack_bundle([bundle_dir], tmp_path / "store")
    manifest = json.loads((rebuilt(tmp_path) / "commits" / COMMIT / "manifest.json").read_text())
    for entry in manifest["files"]:
        path = rebuilt(tmp_path) / "commits" / COMMIT / "files" / entry["path"]
        assert os.path.getsize(path) == entry["size"]
