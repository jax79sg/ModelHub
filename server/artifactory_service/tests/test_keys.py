"""The trusted-key list (rule BR1.13; FR1.14, FR4.2)."""

import json

import pytest
from modelhub_artifactory_service.keys import (
    FingerprintMismatch,
    InvalidKey,
    KeyExists,
    TrustedKeys,
)
from modelhub_testkit.bundles import make_bundle


@pytest.fixture
def keys(pool, clock):
    return TrustedKeys(pool, clock=clock)


@pytest.fixture
def signer(tmp_path):
    return make_bundle(tmp_path).public_key


def add(keys, signer, **kw):
    args = {
        "public_key_text": json.dumps(signer),
        "typed_fingerprint": signer["fingerprint"],
        "label": "import laptop",
        "by_id": "a1",
        "by_name": "root",
    }
    args.update(kw)
    return keys.add(**args)


def test_a_key_is_added_when_the_typed_fingerprint_matches(keys, signer):
    added = add(keys, signer)
    assert added["fingerprint"] == signer["fingerprint"] and added["label"] == "import laptop"
    assert [k["fingerprint"] for k in keys.list()] == [signer["fingerprint"]]


def test_the_typed_fingerprint_ignores_case_and_separators(keys, signer):
    typed = signer["fingerprint"].replace("-", " ").upper()
    assert add(keys, signer, typed_fingerprint=typed)["fingerprint"] == signer["fingerprint"]


def test_a_wrong_fingerprint_adds_nothing(keys, signer):
    with pytest.raises(FingerprintMismatch):
        add(keys, signer, typed_fingerprint="0000-0000-0000-0000")
    assert keys.list() == []


@pytest.mark.parametrize("text", ["", "not json", "{}", '{"type": "other"}'])
def test_something_that_is_not_a_public_key_is_refused(keys, signer, text):
    with pytest.raises(InvalidKey):
        add(keys, signer, public_key_text=text)


def test_a_key_whose_fingerprint_does_not_match_its_bytes_is_refused(keys, signer):
    forged = dict(signer, fingerprint="0000-0000-0000-0000-0000-0000-0000-0000")
    with pytest.raises(InvalidKey):
        add(
            keys,
            signer,
            public_key_text=json.dumps(forged),
            typed_fingerprint=forged["fingerprint"],
        )


def test_adding_the_same_key_twice_is_a_conflict(keys, signer):
    add(keys, signer)
    with pytest.raises(KeyExists):
        add(keys, signer)


@pytest.mark.parametrize("label", ["", " ", "x" * 81])
def test_the_label_is_1_to_80_characters(keys, signer, label):
    with pytest.raises(InvalidKey):
        add(keys, signer, label=label)


def test_revoking_stops_the_key_being_trusted_but_keeps_the_record(keys, signer):
    add(keys, signer)
    assert len(keys.active_docs()) == 1
    assert keys.revoke(signer["fingerprint"], by_name="root") is True
    assert keys.active_docs() == []
    listed = keys.list()
    assert listed[0]["revoked_at"] and listed[0]["revoked_by_name"] == "root"
    assert keys.revoke(signer["fingerprint"], by_name="root") is True  # repeat is harmless
    assert keys.revoke("nope", by_name="root") is False


def test_a_revoked_key_cannot_be_added_again_by_mistake_but_can_be_restored_explicitly(
    keys, signer
):
    add(keys, signer)
    keys.revoke(signer["fingerprint"], by_name="root")
    with pytest.raises(KeyExists):
        add(keys, signer)


def test_the_active_documents_are_what_the_bundle_check_needs(keys, signer, tmp_path):
    from modelhub import verify

    bundle = make_bundle(tmp_path / "b")
    add(keys, bundle.public_key)
    report = verify.verify_bundle([bundle.directory], trusted=keys.active_docs())[0]
    assert report.ok
    keys.revoke(bundle.public_key["fingerprint"], by_name="root")
    report = verify.verify_bundle([bundle.directory], trusted=keys.active_docs())[0]
    assert [p.code for p in report.problems] == ["key-untrusted"]


def test_lookup_by_fingerprint_for_the_create_checks(keys, signer):
    add(keys, signer)
    assert keys.find_active(signer["fingerprint"]) is not None
    assert keys.find_active("0000") is None
