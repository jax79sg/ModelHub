"""Names, retries and building the Catalog record from an unpacked bundle (BR1.2, BR1.7, BR1.8)."""

import json

import pytest
from modelhub_artifactory_service.names import validate_names
from modelhub_artifactory_service.record_builder import build_record
from modelhub_artifactory_service.retry import RETRY_WAITS, retrying
from modelhub_testkit.bundles import make_bundle

from modelhub import unpack, verify

COMMIT = "a" * 40


# --- names -----------------------------------------------------------------------------------
@pytest.mark.parametrize("model_id", ["acme/tiny", "a-b/Model_1.2", "acme2/m"])
def test_good_names_pass(model_id):
    assert validate_names(model_id, COMMIT) is None


@pytest.mark.parametrize(
    "model_id,field",
    [
        ("-acme/m", "organisation"),
        ("ac--me/m", "organisation"),
        ("12345/m", "organisation"),
        ("acme-/m", "organisation"),
        ("acme/a b", "model"),
        ("acme/a@b", "model"),
        ("acme/", "model"),
        ("noslash", "organisation"),
        ("a/b/c", "model"),
    ],
)
def test_bad_names_name_the_field_and_the_rule(model_id, field):
    problem = validate_names(model_id, COMMIT)
    assert problem is not None and field in problem


def test_a_revision_must_be_a_40_character_commit():
    assert "revision" in validate_names("acme/m", "main")
    assert "revision" in validate_names("acme/m", "g" * 40)


# --- retry -----------------------------------------------------------------------------------
class Boom(Exception):
    pass


def test_the_waits_are_1_2_4_8_16_seconds_with_a_little_random_extra():
    assert RETRY_WAITS == (1, 2, 4, 8, 16)
    waits = []
    attempts = []

    def fn():
        attempts.append(1)
        raise Boom

    with pytest.raises(Boom):
        retrying(fn, retry_on=(Boom,), sleep=waits.append, jitter=lambda: 0.5)
    assert len(attempts) == 6  # the first try and five retries
    assert waits == [1.5, 2.5, 4.5, 8.5, 16.5]


def test_success_after_some_failures_returns_the_value():
    waits, state = [], {"n": 0}

    def fn():
        state["n"] += 1
        if state["n"] < 3:
            raise Boom
        return "ok"

    assert retrying(fn, retry_on=(Boom,), sleep=waits.append, jitter=lambda: 0) == "ok"
    assert waits == [1, 2]


def test_other_errors_are_not_retried():
    attempts = []

    def fn():
        attempts.append(1)
        raise ValueError

    with pytest.raises(ValueError):
        retrying(fn, retry_on=(Boom,), sleep=lambda s: None)
    assert len(attempts) == 1


def test_the_jitter_is_at_most_one_second_by_default():
    waits = []
    with pytest.raises(Boom):
        retrying(lambda: (_ for _ in ()).throw(Boom()), retry_on=(Boom,), sleep=waits.append)
    assert all(base <= w < base + 1 for base, w in zip(RETRY_WAITS, waits, strict=True))


# --- the Catalog record ----------------------------------------------------------------------
@pytest.fixture
def unpacked(tmp_path):
    bundle = make_bundle(tmp_path)
    report = verify.verify_bundle([bundle.directory], trusted=[bundle.public_key])[0]
    out = tmp_path / "unpacked"
    unpack.rebuild_into(report, out)
    return bundle, out


IMPORT = {
    "imported_by_id": "u1",
    "imported_by_name": "ada",
    "imported_at": "2026-02-01T00:00:00Z",
    "computer": "pc1",
    "bundle_name": "bundle-1",
    "tool_version": "1.2.0",
    "check_results": {"ok": True},
    "outcome": "imported",
    "signing_key_fingerprint": "aaaa-bbbb",
}


def test_the_record_carries_the_version_fields_from_summary_json(unpacked):
    bundle, out = unpacked
    record, _ = build_record(out, IMPORT, bundle.description_path, bundle.signature_path)
    v = record["version"]
    assert v["model_id"] == "org/tiny" and v["commit"] == COMMIT
    assert v["license"] == "mit" and v["language"] == ["en"]
    assert v["task"] == "text-generation" and v["library"] == "transformers"
    assert v["downloads"] == 1234 and v["likes"] == 56 and v["parameter_count"] == 10
    assert v["size_bytes"] == 20579 and v["created_at"] == "2025-01-01T00:00:00.000Z"
    assert v["refs"] == [{"name": "main", "kind": "branch", "commit": COMMIT}]


def test_files_have_sizes_checksums_types_and_scan_results(unpacked):
    bundle, out = unpacked
    record, _ = build_record(out, IMPORT, bundle.description_path, bundle.signature_path)
    files = {f["path"]: f for f in record["version"]["files"]}
    assert set(files) == {"README.md", "config.json", "tokenizer.json", "model.safetensors"}
    assert files["config.json"]["size_bytes"] == 23 and len(files["config.json"]["sha256"]) == 64
    assert files["model.safetensors"]["downloaded"] is True
    assert files["README.md"]["safety_scan"] == "safe" and files["README.md"]["file_type"]


def test_a_file_listed_by_the_hub_but_never_downloaded_is_marked_not_downloaded(unpacked):
    bundle, out = unpacked
    tree = json.loads((out / "raw" / "tree.json").read_text())
    tree.append(
        {
            "type": "file",
            "oid": "c" * 40,
            "size": 999,
            "path": "extra.bin",
            "lfs": {"oid": "d" * 64, "size": 999},
        }
    )
    (out / "raw" / "tree.json").write_text(json.dumps(tree))
    record, _ = build_record(out, IMPORT, bundle.description_path, bundle.signature_path)
    extra = next(f for f in record["version"]["files"] if f["path"] == "extra.bin")
    assert (
        extra["downloaded"] is False and extra["size_bytes"] == 999 and extra["sha256"] == "d" * 64
    )


def test_the_documents_are_the_readme_pictures_responses_manifest_and_bundle_files(unpacked):
    bundle, out = unpacked
    _, docs = build_record(out, IMPORT, bundle.description_path, bundle.signature_path)
    names = {(name.split("/", 1)[0], name.split("/", 1)[1]) for name, _, _ in docs}
    assert ("readme", "README.md") in names and ("readme_local", "README.local.md") in names
    assert ("manifest", "manifest.json") in names
    assert ("response", "summary.json") in names and ("response", "raw/model_info.json") in names
    assert any(k == "bundle_description" for k, _ in names)
    assert any(k == "bundle_signature" for k, _ in names)
    by_name = {n: (d, c) for n, d, c in docs}
    assert by_name["readme/README.md"][1].startswith("text/markdown")
    assert by_name["response/summary.json"][1] == "application/json"


def test_the_import_record_is_built_from_the_job(unpacked):
    bundle, out = unpacked
    record, _ = build_record(out, IMPORT, bundle.description_path, bundle.signature_path)
    imp = record["importRecord"]
    assert imp["importedBy"] == {"id": "u1", "name": "ada"}
    assert imp["importedAt"] == "2026-02-01T00:00:00Z" and imp["outcome"] == "imported"
    assert imp["signingKeyFingerprint"] == "aaaa-bbbb" and imp["toolVersion"] == "1.2.0"
    import hashlib

    assert imp["bundleSha256"] == hashlib.sha256(bundle.description_path.read_bytes()).hexdigest()


def test_a_missing_readme_and_unfetched_pictures_are_recorded_as_such(unpacked):
    bundle, out = unpacked
    (out / "files" / "README.md").unlink()
    summary = json.loads((out / "summary.json").read_text())
    summary["readme"] = {
        "original": None,
        "local": None,
        "pictures": [{"source": "https://x.example/a.png", "local": None, "status": "failed"}],
    }
    (out / "summary.json").write_text(json.dumps(summary))
    (out / "readme" / "README.local.md").unlink()
    record, docs = build_record(out, IMPORT, bundle.description_path, bundle.signature_path)
    assert not any(n.startswith("readme/") for n, _, _ in docs)
    pic = [n for n, _, _ in docs if n.startswith("picture/")]
    assert len(pic) == 1
    assert record["version"]["files"]  # still lists the files


def test_a_licence_given_as_a_list_is_stored_as_text(unpacked):
    bundle, out = unpacked
    summary = json.loads((out / "summary.json").read_text())
    summary["card"]["license"] = ["mit", "apache-2.0"]
    (out / "summary.json").write_text(json.dumps(summary))
    record, _ = build_record(out, IMPORT, bundle.description_path, bundle.signature_path)
    assert record["version"]["license"] == "mit, apache-2.0"
