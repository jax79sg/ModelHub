import json

import pytest
from typer.testing import CliRunner

from modelhub import bundle, cli, signing, verify

runner = CliRunner()


@pytest.fixture
def pub(home, tmp_path):
    doc = signing.create_key("download-side")
    signing.export_public(doc["key_id"], tmp_path / "pub.json")
    return doc, tmp_path / "pub.json"


def other_side(tmp_path, monkeypatch):
    """Act as the air-gapped computer: a different home with no keys and no trust."""
    monkeypatch.setenv("MODELHUB_HOME", str(tmp_path / "airgap"))


def test_a_key_is_trusted_only_after_its_fingerprint_is_typed(pub, tmp_path, monkeypatch):
    doc, path = pub
    other_side(tmp_path, monkeypatch)
    assert signing.trusted_keys() == []
    signing.trust_key(signing.read_public_doc(path), doc["fingerprint"])
    assert [k["key_id"] for k in signing.trusted_keys()] == [doc["key_id"]]


def test_a_wrong_fingerprint_does_not_trust_the_key(pub, tmp_path, monkeypatch):
    _, path = pub
    other_side(tmp_path, monkeypatch)
    with pytest.raises(signing.KeyError_, match="does not match"):
        signing.trust_key(signing.read_public_doc(path), "0000-0000-0000-0000-0000-0000-0000-0000")
    assert signing.trusted_keys() == []


@pytest.mark.parametrize("answer", ["yes", "y", "ok", "", "trust"])
def test_agreeing_is_not_enough_the_fingerprint_must_be_typed(pub, tmp_path, monkeypatch, answer):
    _, path = pub
    other_side(tmp_path, monkeypatch)
    with pytest.raises(signing.KeyError_):
        signing.trust_key(signing.read_public_doc(path), answer)
    assert signing.trusted_keys() == []


def test_the_fingerprint_may_be_typed_in_capitals_or_with_spaces(pub, tmp_path, monkeypatch):
    doc, path = pub
    other_side(tmp_path, monkeypatch)
    typed = doc["fingerprint"].upper().replace("-", " ")
    signing.trust_key(signing.read_public_doc(path), typed)
    assert signing.trusted_keys()


def test_cli_trust_asks_for_the_fingerprint_and_refuses_a_wrong_one(pub, tmp_path, monkeypatch):
    doc, path = pub
    other_side(tmp_path, monkeypatch)
    env = {"MODELHUB_HOME": str(tmp_path / "airgap")}
    refused = runner.invoke(cli.app, ["key", "trust", str(path)], input="not-it\n", env=env)
    assert refused.exit_code == 1
    assert "does not match" in refused.output
    accepted = runner.invoke(
        cli.app, ["key", "trust", str(path)], input=doc["fingerprint"] + "\n", env=env
    )
    assert accepted.exit_code == 0
    assert "Trusted key" in accepted.output


def test_cli_trust_with_no_typed_answer_trusts_nothing(pub, tmp_path, monkeypatch):
    _, path = pub
    other_side(tmp_path, monkeypatch)
    env = {"MODELHUB_HOME": str(tmp_path / "airgap")}
    result = runner.invoke(cli.app, ["key", "trust", str(path)], input="", env=env)
    assert result.exit_code != 0
    assert signing.trusted_keys() == []


def test_a_bundle_cannot_vouch_for_its_own_key(pulled, home, tmp_path, monkeypatch):
    doc = signing.create_key("untrusted")
    out = tmp_path / "bundle"
    bundle.bundle_record(pulled, out, doc["key_id"], piece_size=8192)
    signing.export_public(doc["key_id"], out / "public-key.json")  # the key travels with the bundle
    other_side(tmp_path, monkeypatch)
    report = verify.verify_bundle([out])[0]
    assert [p.code for p in report.problems] == ["key-untrusted"]
    assert "does not trust" in report.problems[0].message


def test_untrusting_a_key_makes_its_bundles_fail_with_a_clear_message(bundle_dir):
    [key] = signing.trusted_keys()
    assert verify.verify_bundle([bundle_dir])[0].ok
    assert signing.untrust_key(key["key_id"]) is True
    report = verify.verify_bundle([bundle_dir])[0]
    assert [p.code for p in report.problems] == ["key-untrusted"]
    assert signing.untrust_key(key["key_id"]) is False


def test_a_replacement_key_is_not_trusted_until_its_fingerprint_is_confirmed(
    pulled, key_id, tmp_path, bundle_dir
):
    new = signing.create_key("replacement")
    out = tmp_path / "second"
    bundle.bundle_record(pulled, out, new["key_id"], piece_size=8192)
    assert [p.code for p in verify.verify_bundle([out])[0].problems] == ["key-untrusted"]
    signing.trust_key(new, new["fingerprint"])
    assert verify.verify_bundle([out])[0].ok
    assert verify.verify_bundle([bundle_dir])[
        0
    ].ok  # the old key is still trusted, so old bundles verify


def test_a_bundle_signed_with_a_key_the_signature_file_misnames_is_refused(bundle_dir):
    sig_path = next(bundle_dir.glob("*.bundle.sig"))
    doc = json.loads(sig_path.read_text())
    doc["key_id"] = "0" * 16
    sig_path.write_text(json.dumps(doc))
    assert [p.code for p in verify.verify_bundle([bundle_dir])[0].problems] == ["key-untrusted"]
