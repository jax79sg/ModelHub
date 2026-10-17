"""The signed server pack: a folder carried across the air gap and checked before anything is loaded."""

import json

import pytest
from typer.testing import CliRunner

from modelhub import cli, serverpack, signing

runner = CliRunner()


@pytest.fixture
def pack(tmp_path):
    folder = tmp_path / "pack"
    (folder / "images").mkdir(parents=True)
    (folder / "compose.yaml").write_text("name: modelhub\n")
    (folder / "release.env").write_text("MODELHUB_VERSION=1.2.3\n")
    (folder / "images" / "portal.tar").write_bytes(b"portal image" * 100)
    (folder / "images" / "catalog.tar").write_bytes(b"catalog image" * 100)
    return folder


@pytest.fixture
def trusted(home, key_id):
    """The fingerprint of a signing key made and trusted here (the pack commands accept it)."""
    doc = signing.find_own_key(key_id)
    signing.trust_key(doc, doc["fingerprint"])
    return doc["fingerprint"]


def test_a_signed_pack_verifies_and_lists_what_it_holds(pack, trusted):
    count = serverpack.sign_pack(pack, trusted)
    assert count == 4
    assert serverpack.verify_pack(pack) == []
    lines = (pack / "SHA256SUMS").read_text().splitlines()
    assert [ln.split("  ", 1)[1] for ln in lines] == sorted(
        ["compose.yaml", "release.env", "images/portal.tar", "images/catalog.tar"]
    )


def test_a_changed_file_is_named(pack, trusted):
    serverpack.sign_pack(pack, trusted)
    (pack / "images" / "portal.tar").write_bytes(b"tampered")
    problems = serverpack.verify_pack(pack)
    assert any("images/portal.tar" in p and "does not match" in p for p in problems)


def test_a_missing_file_and_an_extra_file_are_named(pack, trusted):
    serverpack.sign_pack(pack, trusted)
    (pack / "release.env").unlink()
    (pack / "extra.sh").write_text("echo hi")
    problems = serverpack.verify_pack(pack)
    assert any("release.env" in p and "missing" in p for p in problems)
    assert any("extra.sh" in p and "not in the signed list" in p for p in problems)


def test_a_list_that_was_edited_fails_the_signature(pack, trusted):
    serverpack.sign_pack(pack, trusted)
    sums = pack / "SHA256SUMS"
    sums.write_text(sums.read_text().replace("compose.yaml", "compose.yml"))
    problems = serverpack.verify_pack(pack)
    assert any("signature" in p.lower() for p in problems)


def test_a_pack_signed_by_a_key_not_trusted_here_is_refused(pack, home, key_id):
    serverpack.sign_pack(pack, signing.find_own_key(key_id)["fingerprint"])  # never trusted
    problems = serverpack.verify_pack(pack)
    assert any("does not trust" in p for p in problems)


def test_an_unsigned_pack_is_refused(pack, trusted):
    assert any("signature" in p.lower() for p in serverpack.verify_pack(pack))


def test_paths_that_climb_out_of_the_pack_are_refused(pack, trusted):
    serverpack.sign_pack(pack, trusted)
    sums = pack / "SHA256SUMS"
    sums.write_text(sums.read_text() + "a" * 64 + "  ../outside\n")
    sig = signing.sign_bytes(signing.find_own_key(trusted)["key_id"], sums.read_bytes())
    (pack / "SHA256SUMS.sig").write_text(json.dumps(sig))
    assert any("unsafe" in p for p in serverpack.verify_pack(pack))


def test_signing_again_after_a_change_replaces_the_list(pack, trusted):
    serverpack.sign_pack(pack, trusted)
    (pack / "release.env").write_text("MODELHUB_VERSION=1.2.4\n")
    assert serverpack.verify_pack(pack) != []
    serverpack.sign_pack(pack, trusted)
    assert serverpack.verify_pack(pack) == []


def test_the_commands_sign_and_verify_with_exit_statuses(pack, home, key_id, trusted):
    env = {"MODELHUB_HOME": str(home)}
    signed = runner.invoke(cli.app, ["pack", "sign", str(pack), "--key", trusted], env=env)
    assert signed.exit_code == 0, signed.output
    ok = runner.invoke(cli.app, ["pack", "verify", str(pack)], env=env)
    assert ok.exit_code == 0 and "OK" in ok.output
    (pack / "compose.yaml").write_text("changed")
    bad = runner.invoke(cli.app, ["pack", "verify", str(pack)], env=env)
    assert bad.exit_code == 1 and "compose.yaml" in bad.output
    missing = runner.invoke(cli.app, ["pack", "verify", str(pack / "nope")], env=env)
    assert missing.exit_code == 2
