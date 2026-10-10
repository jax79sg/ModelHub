import re
import stat
import sys

import pytest
from typer.testing import CliRunner

from modelhub import cli, signing

runner = CliRunner()


@pytest.fixture
def run(home):
    def _run(*args, input=None):
        return runner.invoke(
            cli.app, [str(a) for a in args], input=input, env={"MODELHUB_HOME": str(home)}
        )

    return _run


def test_creating_a_key_makes_a_private_and_a_public_file(home):
    doc = signing.create_key("laptop")
    assert (home / "keys" / f"{doc['key_id']}.key").is_file()
    assert (home / "keys" / f"{doc['key_id']}.pub.json").is_file()
    assert doc["name"] == "laptop"


@pytest.mark.skipif(sys.platform == "win32", reason="owner-only access on Windows is checked there")
def test_the_private_key_file_is_readable_by_its_owner_only(home):
    doc = signing.create_key("laptop")
    mode = stat.S_IMODE((home / "keys" / f"{doc['key_id']}.key").stat().st_mode)
    assert mode == 0o600


def test_the_fingerprint_is_short_and_readable(home):
    fingerprint = signing.create_key("k")["fingerprint"]
    assert re.fullmatch(r"([0-9a-f]{4}-){7}[0-9a-f]{4}", fingerprint)


def test_the_exported_file_gives_the_same_fingerprint_as_the_original(home, tmp_path):
    doc = signing.create_key("k")
    signing.export_public(doc["key_id"], tmp_path / "pub.json")
    assert signing.read_public_doc(tmp_path / "pub.json")["fingerprint"] == doc["fingerprint"]


def test_the_exported_file_holds_no_private_material(home, tmp_path):
    doc = signing.create_key("k")
    signing.export_public(doc["key_id"], tmp_path / "pub.json")
    text = (tmp_path / "pub.json").read_text()
    assert "PRIVATE" not in text
    private = (home / "keys" / f"{doc['key_id']}.key").read_text()
    body = "".join(private.splitlines()[1:-1])
    assert body not in text


def test_a_public_file_whose_fingerprint_does_not_match_its_key_is_rejected(home, tmp_path):
    doc = signing.create_key("k")
    signing.export_public(doc["key_id"], tmp_path / "pub.json")
    other = signing.create_key("other")
    text = (tmp_path / "pub.json").read_text().replace(doc["fingerprint"], other["fingerprint"])
    (tmp_path / "pub.json").write_text(text)
    with pytest.raises(signing.KeyError_, match="does not match"):
        signing.read_public_doc(tmp_path / "pub.json")


def test_a_file_that_is_not_a_public_key_is_rejected(home, tmp_path):
    (tmp_path / "x.json").write_text('{"hello": 1}')
    with pytest.raises(signing.KeyError_):
        signing.read_public_doc(tmp_path / "x.json")


def trust_self(doc):
    signing.trust_key(doc, doc["fingerprint"])


def test_a_signature_checks_out_only_for_the_exact_data(home):
    doc = signing.create_key("k")
    trust_self(doc)
    sig = signing.sign_bytes(doc["key_id"], b"manifest")
    assert signing.verify_signature(sig, b"manifest")["key_id"] == doc["key_id"]
    with pytest.raises(signing.SignatureProblem) as error:
        signing.verify_signature(sig, b"manifesT")
    assert error.value.code == "signature-invalid"


def test_no_signature_is_its_own_problem(home):
    with pytest.raises(signing.SignatureProblem) as error:
        signing.verify_signature(None, b"x")
    assert error.value.code == "signature-missing"


def test_one_key_is_chosen_automatically_but_two_need_a_choice(home):
    with pytest.raises(signing.KeyError_, match="no signing key"):
        signing.default_key_id()
    first = signing.create_key("a")
    assert signing.default_key_id() == first["key_id"]
    signing.create_key("b")
    with pytest.raises(signing.KeyError_, match="more than one"):
        signing.default_key_id()


def test_cli_create_prints_the_key_and_its_fingerprint(run):
    result = run("key", "create", "--name", "laptop")
    assert result.exit_code == 0
    assert "Created key" in result.output and "Fingerprint:" in result.output


def test_cli_list_shows_own_and_trusted_keys(run, home, tmp_path):
    created = run("key", "create")
    key_id = re.search(r"Created key (\S+)", created.output).group(1)
    run("key", "export", key_id, "--out", tmp_path / "p.json")
    fingerprint = signing.read_public_doc(tmp_path / "p.json")["fingerprint"]
    run("key", "trust", tmp_path / "p.json", input=fingerprint + "\n")
    listed = run("key", "list").output
    assert "own" in listed and "trusted" in listed and key_id in listed


def test_cli_fingerprint_works_for_a_key_id_or_a_file(run, tmp_path):
    created = run("key", "create")
    key_id = re.search(r"Created key (\S+)", created.output).group(1)
    by_id = run("key", "fingerprint", key_id).output
    run("key", "export", key_id, "--out", tmp_path / "p.json")
    by_file = run("key", "fingerprint", tmp_path / "p.json").output
    assert by_id == by_file and "Fingerprint:" in by_id
