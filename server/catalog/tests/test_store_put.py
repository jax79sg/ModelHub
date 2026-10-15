"""Storing a version (rules BR1.1, BR1.2, BR1.7, BR1.10, BR1.12, BR1.13; FR2.x; AC2.1, AC2.2)."""

import copy

import psycopg
import pytest
from conftest import C1, C2, make_docs, make_record
from modelhub_catalog.records import InvalidRecord
from modelhub_catalog.store import Document, RecordConflict, StoreFailed


def count(url, table):
    with psycopg.connect(url) as conn:
        return conn.execute(f"select count(*) from {table}").fetchone()[0]  # noqa: S608


def test_a_first_store_writes_everything_and_one_trail_row(store, put, fresh_database):
    result = put()
    assert result.status == "created"
    for table, n in [
        ("models", 1),
        ("model_versions", 1),
        ("version_files", 2),
        ("refs", 1),
        ("documents", 2),
        ("import_records", 1),
        ("model_summary", 1),
    ]:
        assert count(fresh_database, table) == n, table


def test_an_identical_repeat_changes_nothing_and_adds_no_trail_row(put, fresh_database):
    put()
    result = put()
    assert result.status == "unchanged"
    assert count(fresh_database, "import_records") == 1
    assert count(fresh_database, "documents") == 2


def test_the_time_of_the_import_does_not_make_a_repeat_different(put):
    put()
    assert put(importRecord={"importedAt": "2027-01-01T00:00:00Z"}).status == "unchanged"


def test_a_different_record_for_the_same_commit_is_refused_and_changes_nothing(
    put, store, fresh_database
):
    put()
    with pytest.raises(RecordConflict):
        put(version={"likes": 99})
    v = store.get_version("acme/tiny", C1)
    assert v["likes"] == 10
    assert count(fresh_database, "import_records") == 1


def test_a_failure_part_way_leaves_nothing_behind(store, fresh_database):
    with psycopg.connect(fresh_database, autocommit=True) as conn:
        conn.execute(
            "create function boom() returns trigger language plpgsql as "
            "$$ begin raise exception 'imitated failure'; end $$"
        )
        conn.execute(
            "create trigger t before insert on import_records for each row execute function boom()"
        )
    with pytest.raises(StoreFailed):
        store.put_version("acme/tiny", C1, make_record(), make_docs())
    for table in [
        "models",
        "model_versions",
        "version_files",
        "documents",
        "model_summary",
        "import_records",
        "refs",
    ]:
        assert count(fresh_database, table) == 0, table


def test_an_invalid_record_stores_nothing(store, fresh_database):
    bad = make_record()
    bad["importRecord"].pop("computer")
    with pytest.raises(InvalidRecord):
        store.put_version("acme/tiny", C1, bad, make_docs())
    assert count(fresh_database, "models") == 0


def test_a_value_not_given_is_stored_as_null_and_zero_stays_zero(put, store):
    put(version={"downloads": None, "likes": 0})
    v = store.get_version("acme/tiny", C1)
    assert v["downloads"] is None and v["likes"] == 0


def test_unknown_fields_in_the_record_do_not_stop_the_store(put):
    r = make_record(version={"newField": [1, 2]})
    assert put(version=r["version"]).status == "created"


def test_the_model_id_is_the_same_model_whatever_the_case(put, store, fresh_database):
    put("Acme/Tiny", commit=C1, version={"model_id": "Acme/Tiny"})
    put("acme/tiny", commit=C2, version={"model_id": "acme/tiny"})
    assert count(fresh_database, "models") == 1
    assert store.get_model("ACME/TINY")["model_id"] == "Acme/Tiny"  # as first imported


def test_a_missing_readme_licence_file_and_unfetched_picture_are_stored_as_such(put, store):
    docs = [
        Document("response", "m.json", "application/json", b"{}"),
        Document("picture", "p.png", "image/png", b"", picture_status="unfetched"),
        Document("licence", "LICENSE", "text/plain", b"Apache"),
    ]
    put(docs=docs, version={"license": None})
    v = store.get_version("acme/tiny", C1)
    assert v["has_readme"] is False and v["license"] is None
    names = {(d["kind"], d["name"]): d for d in v["documents"]}
    assert names[("picture", "p.png")]["picture_status"] == "unfetched"
    assert ("licence", "LICENSE") in names
    f = {x["path"]: x for x in v["files"]}
    assert (
        f["model.safetensors"]["downloaded"] is False and f["model.safetensors"]["sha256"] is None
    )


def test_the_summary_follows_the_imported_version_with_the_latest_import_time(put, store):
    put(commit=C1, importRecord={"importedAt": "2026-02-01T00:00:00Z"}, version={"likes": 1})
    put(commit=C2, importRecord={"importedAt": "2026-03-01T00:00:00Z"}, version={"likes": 2})
    item = store.list_models({})["items"][0]
    assert item["latest_commit"] == C2 and item["likes"] == 2
    # an older import arriving later does not take over
    put(commit="3" * 40, importRecord={"importedAt": "2026-01-01T00:00:00Z"}, version={"likes": 3})
    assert store.list_models({})["items"][0]["latest_commit"] == C2


def test_an_import_only_record_adds_one_trail_row_and_nothing_else(put, store, fresh_database):
    put()
    rec = make_record(importRecord={"outcome": "skipped"})
    del rec["version"]
    result = store.put_import_only("acme/tiny", C1, rec)
    assert result.status == "recorded"
    assert count(fresh_database, "import_records") == 2
    assert count(fresh_database, "model_versions") == 1
    outcomes = [t["outcome"] for t in store.trail()["items"]]
    assert outcomes == ["skipped", "imported"] or sorted(outcomes) == ["imported", "skipped"]


def test_an_import_only_record_needs_an_imported_version(store):
    rec = make_record(importRecord={"outcome": "repaired"})
    del rec["version"]
    with pytest.raises(InvalidRecord):
        store.put_import_only("acme/tiny", C1, rec)


def test_an_import_only_record_cannot_say_imported(put, store):
    put()
    rec = make_record()
    del rec["version"]
    with pytest.raises(InvalidRecord):
        store.put_import_only("acme/tiny", C1, rec)


def test_two_stores_of_the_same_version_at_once_leave_one_version_and_one_trail_row(
    store, fresh_database
):
    from concurrent.futures import ThreadPoolExecutor

    def go(_):
        try:
            return store.put_version(
                "acme/tiny", C1, copy.deepcopy(make_record()), make_docs()
            ).status
        except RecordConflict:
            return "conflict"

    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(go, range(4)))
    assert results.count("created") == 1
    assert set(results) <= {"created", "unchanged"}
    assert count(fresh_database, "import_records") == 1
