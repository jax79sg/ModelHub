"""The models list, search, versions, documents, removal and the trail (BR1.7 to BR1.13, BR1.20)."""

import pytest
from conftest import C1, C2, C3
from modelhub_catalog.store import Document, DocumentGone, InvalidQuery


def seed(put):
    """Three models with different values, imported at different times by two people."""
    put(
        "acme/alpha",
        C1,
        version={
            "model_id": "acme/alpha",
            "task": "text-generation",
            "library": "transformers",
            "license": "mit",
            "language": ["en"],
            "parameter_count": 500_000_000,
            "downloads": 300,
            "likes": 5,
            "tags": ["llama", "chat"],
            "last_modified_at": "2026-01-01T00:00:00Z",
        },
        importRecord={
            "importedAt": "2026-02-01T00:00:00Z",
            "importedBy": {"id": "u1", "name": "ada"},
        },
        docs=[Document("readme", "README.md", "text/markdown", b"A quantized chat model")],
    )
    put(
        "acme/beta",
        C2,
        version={
            "model_id": "acme/beta",
            "task": "fill-mask",
            "library": "transformers",
            "license": "apache-2.0",
            "language": ["en", "fr"],
            "parameter_count": 7_000_000_000,
            "downloads": 900,
            "likes": 50,
            "tags": ["bert"],
            "last_modified_at": "2026-03-01T00:00:00Z",
        },
        importRecord={
            "importedAt": "2026-03-01T00:00:00Z",
            "importedBy": {"id": "u2", "name": "bob"},
        },
        docs=[Document("readme", "README.md", "text/markdown", b"Masked language modelling")],
    )
    put(
        "other/gamma-gguf",
        C3,
        version={
            "model_id": "other/gamma-gguf",
            "task": "text-generation",
            "library": "gguf",
            "license": None,
            "language": None,
            "parameter_count": None,
            "downloads": None,
            "likes": None,
            "tags": ["gguf-q4"],
        },
        importRecord={
            "importedAt": "2026-04-01T00:00:00Z",
            "importedBy": {"id": "u1", "name": "ada"},
        },
        docs=[Document("readme", "README.md", "text/markdown", b"Tiny runner")],
    )


def ids(result):
    return [i["model_id"] for i in result["items"]]


# --- list: filters, sort, paging -------------------------------------------------------------
def test_the_default_sort_is_downloads_largest_first_with_nulls_last(put, store):
    seed(put)
    assert ids(store.list_models({})) == ["acme/beta", "acme/alpha", "other/gamma-gguf"]


@pytest.mark.parametrize(
    "sort,expected",
    [
        ("likes", ["acme/beta", "acme/alpha", "other/gamma-gguf"]),
        ("lastModified", ["acme/beta", "acme/alpha", "other/gamma-gguf"]),
        ("importedAt", ["other/gamma-gguf", "acme/beta", "acme/alpha"]),
        ("name", ["acme/alpha", "acme/beta", "other/gamma-gguf"]),
    ],
)
def test_each_sort_choice(put, store, sort, expected):
    seed(put)
    assert ids(store.list_models({"sort": sort})) == expected


def test_filters_combine_with_and(put, store):
    seed(put)
    assert ids(store.list_models({"task": "text-generation"})) == ["acme/alpha", "other/gamma-gguf"]
    assert ids(store.list_models({"task": "text-generation", "library": "transformers"})) == [
        "acme/alpha"
    ]
    assert ids(store.list_models({"license": "apache-2.0"})) == ["acme/beta"]
    assert ids(store.list_models({"language": "fr"})) == ["acme/beta"]


def test_a_filter_that_matches_nothing_is_an_empty_list_not_an_error(put, store):
    seed(put)
    r = store.list_models({"task": "no-such-task"})
    assert r["items"] == [] and r["total"] == 0


@pytest.mark.parametrize(
    "band,expected",
    [("lt1b", ["acme/alpha"]), ("6b", []), ("12b", ["acme/beta"]), ("gt500b", [])],
)
def test_parameter_size_bands(put, store, band, expected):
    seed(put)
    assert ids(store.list_models({"parameters": band})) == expected


def test_filter_and_sort_by_importer_and_import_time(put, store):
    seed(put)
    r = store.list_models({"importedBy": "u1", "sort": "importedAt"})
    assert ids(r) == ["other/gamma-gguf", "acme/alpha"]
    r = store.list_models(
        {"importedFrom": "2026-02-15T00:00:00Z", "importedTo": "2026-03-15T00:00:00Z"}
    )
    assert ids(r) == ["acme/beta"]


def test_paging_and_the_total(put, store):
    seed(put)
    r = store.list_models({"pageSize": 2, "page": 2})
    assert ids(r) == ["other/gamma-gguf"] and r["total"] == 3 and r["page"] == 2


def test_the_page_size_is_capped_at_100_and_defaults_to_30(put, store):
    seed(put)
    assert store.list_models({})["pageSize"] == 30
    assert store.list_models({"pageSize": 1000})["pageSize"] == 100


@pytest.mark.parametrize(
    "q",
    [
        {"sort": "bogus"},
        {"parameters": "huge"},
        {"page": 0},
        {"pageSize": 0},
        {"page": "x"},
        {"importedFrom": "not-a-time"},
    ],
)
def test_an_unknown_value_is_an_invalid_query(store, q):
    with pytest.raises(InvalidQuery):
        store.list_models(q)


def test_facets_count_each_filter_value(put, store):
    seed(put)
    f = store.list_models({})["facets"]
    assert f["task"] == {"text-generation": 2, "fill-mask": 1}
    assert f["library"]["transformers"] == 2 and f["library"]["gguf"] == 1
    assert f["importedBy"]["ada"] == 2 or f["importedBy"].get("u1") == 2


def test_the_list_never_reads_the_documents_table():
    from modelhub_catalog import store as store_module

    assert store_module.LIST_SQL_TABLES == ("model_summary",)


# --- search ----------------------------------------------------------------------------------
def test_a_whole_word_in_the_card_text_finds_the_model_with_word_forms(put, store):
    seed(put)
    assert ids(store.list_models({"q": "quantize"})) == ["acme/alpha"]
    assert ids(store.list_models({"q": "quantized"})) == ["acme/alpha"]


def test_parts_of_words_match_model_ids_and_tags(put, store):
    seed(put)
    assert ids(store.list_models({"q": "gguf"})) == ["other/gamma-gguf"]
    assert ids(store.list_models({"q": "ama"})) == ["acme/alpha"]  # part of the tag 'llama'


def test_every_word_must_match_somewhere(put, store):
    seed(put)
    assert ids(store.list_models({"q": "quantized chat"})) == ["acme/alpha"]
    assert ids(store.list_models({"q": "quantized bert"})) == []
    assert ids(store.list_models({"q": "quantized llama"})) == ["acme/alpha"]


def test_a_short_word_matches_card_text_only_not_parts_of_ids(put, store):
    seed(put)
    assert ids(store.list_models({"q": "ga"})) == []


def test_an_empty_search_is_ignored_and_a_long_one_is_refused(put, store):
    seed(put)
    assert len(store.list_models({"q": "  "})["items"]) == 3
    with pytest.raises(InvalidQuery):
        store.list_models({"q": "x" * 201})
    with pytest.raises(InvalidQuery):
        store.list_models({"q": " ".join(f"w{i}" for i in range(11))})


def test_search_is_safe_against_hostile_text(put, store):
    seed(put)
    for q in ["'; drop table models; --", "%", "_", "\\", "a & b | !c", "(((", "ünï"]:
        store.list_models({"q": q})
    assert store.list_models({})["total"] == 3


# --- model, version, documents -----------------------------------------------------------------
def test_a_model_lists_its_versions_and_refs(put, store):
    put(commit=C1)
    put(commit=C2, importRecord={"importedAt": "2026-03-01T00:00:00Z"})
    m = store.get_model("acme/tiny")
    assert {v["commit"] for v in m["versions"]} == {C1, C2}
    assert {v["state"] for v in m["versions"]} == {"imported"}
    assert any(r["name"] == "main" for r in m["refs"])
    assert store.get_model("nope/none") is None


def test_a_version_record_has_files_and_a_document_list_without_content(put, store):
    put()
    v = store.get_version("acme/tiny", C1)
    assert all("content" not in d for d in v["documents"])
    assert {d["kind"] for d in v["documents"]} == {"readme", "response"}
    assert store.get_version("acme/tiny", C2) is None


def test_a_document_is_served_with_its_bytes_and_type(put, store):
    put()
    data, ctype = store.get_document("acme/tiny", C1, "readme", "README.md")
    assert data.startswith(b"# Tiny") and ctype == "text/markdown"
    assert store.get_document("acme/tiny", C1, "readme", "nope.md") is None


# --- removal, reinstatement -------------------------------------------------------------------
def test_removal_keeps_the_record_files_and_trail_but_drops_document_content(put, store):
    put()
    assert store.mark_removed("acme/tiny", C1, removed_by="admin1") == "ok"
    v = store.get_version("acme/tiny", C1)
    assert v["state"] == "removed" and v["removed_by"] == "admin1" and v["removed_at"]
    assert len(v["files"]) == 2 and len(v["documents"]) == 2  # rows kept
    with pytest.raises(DocumentGone):
        store.get_document("acme/tiny", C1, "readme", "README.md")
    assert len(store.trail()["items"]) == 1


def test_a_removed_version_is_hidden_from_the_list_unless_asked_and_search_forgets_its_card(
    put, store
):
    put()
    store.mark_removed("acme/tiny", C1, removed_by="admin1")
    assert store.list_models({})["items"] == []
    shown = store.list_models({"showRemoved": True})["items"]
    assert shown and shown[0]["state"] == "removed"
    assert store.list_models({"q": "quantized", "showRemoved": True})["items"] == []
    assert store.list_models({"q": "tiny", "showRemoved": True})["items"]  # by id


def test_removing_twice_or_a_missing_version_is_a_conflict(put, store):
    put()
    assert store.mark_removed("acme/tiny", C1, removed_by="a") == "ok"
    assert store.mark_removed("acme/tiny", C1, removed_by="a") == "conflict"
    assert store.mark_removed("acme/tiny", C2, removed_by="a") == "conflict"


def test_the_summary_moves_to_the_next_imported_version_when_one_is_removed(put, store):
    put(commit=C1, importRecord={"importedAt": "2026-02-01T00:00:00Z"})
    put(commit=C2, importRecord={"importedAt": "2026-03-01T00:00:00Z"})
    store.mark_removed("acme/tiny", C2, removed_by="a")
    item = store.list_models({})["items"][0]
    assert item["latest_commit"] == C1 and item["state"] == "imported"


def test_a_new_import_of_a_removed_version_brings_it_back(put, store):
    put()
    store.mark_removed("acme/tiny", C1, removed_by="a")
    result = put(importRecord={"importedAt": "2026-06-01T00:00:00Z"})
    assert result.status == "reinstated"
    v = store.get_version("acme/tiny", C1)
    assert v["state"] == "imported" and v["removed_at"] is None
    data, _ = store.get_document("acme/tiny", C1, "readme", "README.md")
    assert data.startswith(b"# Tiny")
    outcomes = [t["outcome"] for t in store.trail()["items"]]
    assert len(outcomes) == 2
    assert store.list_models({})["items"][0]["state"] == "imported"


# --- trail and the retention list -------------------------------------------------------------
def test_the_trail_is_newest_first_and_filters_by_model_and_person(put, store):
    seed(put)
    t = store.trail()
    assert [i["model_id"] for i in t["items"]] == ["other/gamma-gguf", "acme/beta", "acme/alpha"]
    assert [i["model_id"] for i in store.trail(person_id="u1")["items"]] == [
        "other/gamma-gguf",
        "acme/alpha",
    ]
    assert [i["model_id"] for i in store.trail(model_id="ACME/beta")["items"]] == ["acme/beta"]
    row = t["items"][0]
    assert row["imported_by_name"] == "ada" and row["computer"] == "pc1"
    assert row["signing_key_fingerprint"] and row["outcome"] == "imported"


def test_the_retention_list_is_oldest_first_with_minimum_fields(put, store):
    seed(put)
    r = store.versions_for_retention(state="imported", imported_before="2026-03-15T00:00:00Z")
    assert [v["model_id"] for v in r["items"]] == ["acme/alpha", "acme/beta"]
    assert set(r["items"][0]) == {
        "versionKey",
        "model_id",
        "commit",
        "imported_at",
        "imported_by",
        "size_bytes",
    }
    store.mark_removed("acme/alpha", C1, removed_by="x")
    assert [v["model_id"] for v in store.versions_for_retention(state="removed")["items"]] == [
        "acme/alpha"
    ]
    with pytest.raises(InvalidQuery):
        store.versions_for_retention(state="weird")
