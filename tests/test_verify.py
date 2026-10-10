import json
import shutil

import pytest
from typer.testing import CliRunner

from modelhub import cli, signing, verify

runner = CliRunner()


def pieces_of(bundle_dir):
    return sorted(p for p in bundle_dir.glob("*.part-*") if not p.name.startswith("."))


def problems_of(reports):
    return [(p.code, p.piece) for r in reports for p in r.problems]


def test_a_good_bundle_is_ok(bundle_dir):
    reports = verify.verify_bundle([bundle_dir])
    assert len(reports) == 1 and reports[0].ok


def test_every_missing_and_damaged_piece_is_named_in_one_run(bundle_dir):
    files = pieces_of(bundle_dir)
    files[1].unlink()
    data = bytearray(files[3].read_bytes())
    data[10] ^= 0xFF
    files[3].write_bytes(bytes(data))
    files[4].write_bytes(files[4].read_bytes()[:-1])
    found = problems_of(verify.verify_bundle([bundle_dir]))
    assert (("piece-missing", files[1].name)) in found
    assert (("piece-damaged", files[3].name)) in found
    assert (("piece-damaged", files[4].name)) in found
    assert len(found) == 3  # nothing else is reported


def test_replacing_one_damaged_piece_needs_no_other_piece(bundle_dir, tmp_path):
    files = pieces_of(bundle_dir)
    spare = tmp_path / "spare"
    spare.mkdir()
    shutil.copy(files[2], spare / files[2].name)
    files[2].write_bytes(b"garbage")
    assert not verify.verify_bundle([bundle_dir])[0].ok
    shutil.copy(spare / files[2].name, files[2])
    assert verify.verify_bundle([bundle_dir])[0].ok


def test_pieces_spread_over_several_folders_verify_in_any_order(bundle_dir, tmp_path):
    second = tmp_path / "second"
    second.mkdir()
    for piece in pieces_of(bundle_dir)[::2]:
        shutil.move(piece, second / piece.name)
    assert verify.verify_bundle([bundle_dir, second])[0].ok
    assert verify.verify_bundle([second, bundle_dir])[0].ok


def test_the_pieces_still_missing_are_listed_by_name(bundle_dir, tmp_path):
    second = tmp_path / "second"
    second.mkdir()
    moved = pieces_of(bundle_dir)[::2]
    for piece in moved:
        shutil.move(piece, second / piece.name)
    report = verify.verify_bundle([bundle_dir])[0]
    assert {p.piece for p in report.problems} == {m.name for m in moved}


def test_a_bundle_made_by_a_newer_incompatible_version_is_refused(bundle_dir):
    manifest_path = next(bundle_dir.glob("*.bundle.json"))
    doc = json.loads(manifest_path.read_text())
    doc["format_version"] = "99.0"
    manifest_path.write_text(json.dumps(doc))
    # the newer tool signed its own manifest, so the signature itself is genuine
    key_id = signing.trusted_keys()[0]["key_id"]
    sig = signing.sign_bytes(key_id, manifest_path.read_bytes())
    manifest_path.with_name(manifest_path.name.replace(".json", ".sig")).write_text(json.dumps(sig))
    found = problems_of(verify.verify_bundle([bundle_dir]))
    assert ("unsupported-format", None) in found


@pytest.fixture
def run(home):
    def _run(*args):
        return runner.invoke(cli.app, [str(a) for a in args], env={"MODELHUB_HOME": str(home)})

    return _run


def test_cli_verify_ends_zero_for_a_good_bundle(run, bundle_dir):
    result = run("verify", bundle_dir)
    assert result.exit_code == 0, result.output
    assert "OK" in result.output


def test_cli_verify_ends_one_and_names_each_bad_piece(run, bundle_dir):
    files = pieces_of(bundle_dir)
    files[0].unlink()
    files[1].write_bytes(b"x")
    result = run("verify", bundle_dir)
    assert result.exit_code == 1
    assert files[0].name in result.output and files[1].name in result.output


def test_cli_verify_ends_two_when_there_is_no_bundle_to_check(run, tmp_path):
    (tmp_path / "empty").mkdir()
    result = run("verify", tmp_path / "empty")
    assert result.exit_code == 2
    assert "no bundle found" in result.output
