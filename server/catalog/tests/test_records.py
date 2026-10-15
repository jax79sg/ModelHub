"""Record validation and the stored checksum (rules BR1.2, BR1.3, BR1.4, BR1.19; NFR5.6, NFR7.5)."""

import copy

import pytest
from conftest import C1, make_docs, make_record
from modelhub_catalog.records import InvalidRecord, checksum, validate_record
from modelhub_catalog.store import Document


def check(record=None, docs=None, model="acme/tiny", commit=C1):
    return validate_record(model, commit, record or make_record(), docs or make_docs())


def bad(**kw):
    with pytest.raises(InvalidRecord) as err:
        check(**kw)
    return err.value


def test_a_good_record_validates_and_comes_back_normalised():
    v = check()
    assert v.model_id == "acme/tiny" and v.commit == C1
    assert v.version["downloads"] == 1000
    assert v.has_readme is True and "quantized" in v.card_text


@pytest.mark.parametrize("commit", ["abc", "G" * 40, "1" * 39, "1" * 41, ""])
def test_a_commit_must_be_40_hex_characters(commit):
    r = make_record(commit="1" * 40)
    with pytest.raises(InvalidRecord) as err:
        validate_record("acme/tiny", commit, r, make_docs())
    assert "commit" in err.value.field


def test_the_commit_in_the_record_must_match_the_address():
    r = make_record(commit="2" * 40)
    with pytest.raises(InvalidRecord):
        validate_record("acme/tiny", C1, r, make_docs())


def test_an_empty_model_id_is_refused():
    with pytest.raises(InvalidRecord):
        validate_record("", C1, make_record(model=""), make_docs())


@pytest.mark.parametrize(
    "field",
    [
        "importedBy",
        "importedAt",
        "computer",
        "bundleName",
        "bundleSha256",
        "signingKeyFingerprint",
        "toolVersion",
        "checkResults",
        "outcome",
    ],
)
def test_every_import_field_is_required(field):
    r = make_record()
    del r["importRecord"][field]
    assert field in bad(record=r).field


def test_the_outcome_must_be_one_the_trail_knows():
    r = make_record(importRecord={"outcome": "exploded"})
    assert "outcome" in bad(record=r).field


def test_captured_at_must_be_a_time():
    r = make_record(version={"captured_at": "yesterday-ish"})
    assert "captured_at" in bad(record=r).field


def test_a_file_path_must_be_safe_and_unique():
    for path in ["", "/abs", "../up", "a/../b"]:
        r = make_record()
        r["version"]["files"][0]["path"] = path
        assert "path" in bad(record=r).field
    r = make_record()
    r["version"]["files"][1]["path"] = "config.json"
    assert "path" in bad(record=r).field


def test_sizes_cannot_be_negative_and_checksums_must_be_hex():
    r = make_record()
    r["version"]["files"][0]["size_bytes"] = -1
    assert "size" in bad(record=r).field
    r = make_record()
    r["version"]["files"][0]["sha256"] = "xyz"
    assert "sha256" in bad(record=r).field


def test_a_missing_count_is_stored_as_null_never_zero():
    r = make_record(version={"downloads": None, "likes": "", "parameter_count": None})
    v = check(record=r)
    assert v.version["downloads"] is None
    assert v.version["likes"] is None
    assert v.version["parameter_count"] is None


def test_an_absent_count_is_also_null_and_a_real_zero_stays_zero():
    r = make_record(version={"likes": 0})
    del r["version"]["downloads"]
    v = check(record=r)
    assert v.version["downloads"] is None and v.version["likes"] == 0


def test_a_count_that_is_not_a_number_is_refused():
    r = make_record(version={"downloads": "lots"})
    assert "downloads" in bad(record=r).field


def test_unknown_fields_do_not_stop_the_store():
    r = make_record(version={"brand_new": {"x": 1}})
    r["somethingElse"] = True
    assert check(record=r).version["downloads"] == 1000


def test_documents_need_safe_names_and_a_size_limit():
    for name in ["../x", "/abs", ""]:
        with pytest.raises(InvalidRecord):
            check(docs=[Document("readme", name, "text/plain", b"x")])
    big = Document("picture", "p.png", "image/png", b"0" * (16 * 1024 * 1024 + 1))
    assert "document" in bad(docs=[*make_docs(), big]).field


def test_a_document_name_cannot_repeat_within_its_kind():
    docs = [*make_docs(), Document("readme", "README.md", "text/plain", b"again")]
    assert "document" in bad(docs=docs).field


def test_a_stated_document_checksum_must_match_the_content():
    r = make_record()
    r["documentChecksums"] = {"readme/README.md": "0" * 64}
    assert "checksum" in bad(record=r).field


def test_a_model_with_no_readme_is_stored_as_having_none():
    v = check(docs=[Document("response", "m.json", "application/json", b"{}")])
    assert v.has_readme is False and v.card_text is None


def test_a_picture_that_could_not_be_fetched_is_kept_as_such():
    docs = [
        *make_docs(),
        Document("picture", "a.png", "image/png", b"", picture_status="unfetched"),
    ]
    v = check(docs=docs)
    assert [d.picture_status for d in v.documents if d.kind == "picture"] == ["unfetched"]


def test_the_number_of_files_and_documents_is_limited():
    r = make_record()
    r["version"]["files"] = [
        {"path": f"f{i}", "size_bytes": 1, "sha256": None, "downloaded": False}
        for i in range(10_001)
    ]
    assert "files" in bad(record=r).field
    docs = [Document("response", f"r{i}", "application/json", b"{}") for i in range(1001)]
    assert "documents" in bad(docs=docs).field


def test_the_documents_together_are_limited_to_64_mib():
    docs = [
        Document("picture", f"p{i}.png", "image/png", b"0" * (15 * 1024 * 1024)) for i in range(5)
    ]
    assert "documents" in bad(docs=docs).field


# --- checksum -------------------------------------------------------------------------------
def test_the_checksum_ignores_the_time_of_the_import_but_not_the_content():
    a = check(record=make_record(importRecord={"importedAt": "2026-02-01T00:00:00Z"}))
    b = check(record=make_record(importRecord={"importedAt": "2027-09-09T00:00:00Z"}))
    assert checksum(a) == checksum(b)
    c = check(record=make_record(version={"likes": 11}))
    assert checksum(a) != checksum(c)


def test_the_checksum_changes_with_a_document():
    a = check()
    other = copy.deepcopy(make_docs())
    other[0] = Document("readme", "README.md", "text/markdown", b"different")
    assert checksum(a) != checksum(check(docs=other))


def test_the_checksum_does_not_depend_on_the_order_of_documents_or_files():
    docs = make_docs()
    r = make_record()
    r2 = copy.deepcopy(r)
    r2["version"]["files"].reverse()
    assert checksum(check(record=r, docs=docs)) == checksum(check(record=r2, docs=docs[::-1]))
