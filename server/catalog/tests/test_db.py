"""Schema and upgrade steps (rule BR1.21, NFR4.5, NFR5.3)."""

import threading
import uuid

import psycopg
import pytest
from modelhub_catalog import db

PW1 = "p" + uuid.uuid4().hex
PW2 = "p" + uuid.uuid4().hex


def tables(url):
    with psycopg.connect(url) as conn:
        rows = conn.execute(
            "select table_name from information_schema.tables where table_schema = 'public'"
        ).fetchall()
    return {r[0] for r in rows}


def test_migrate_creates_the_tables_the_design_names(fresh_database):
    db.migrate(fresh_database)
    assert {
        "models",
        "model_versions",
        "version_files",
        "refs",
        "documents",
        "import_records",
        "model_summary",
        "personal_tokens",
        "catalog_settings",
        "schema_steps",
    } <= tables(fresh_database)


def test_migrate_twice_changes_nothing_and_records_each_step_once(fresh_database):
    db.migrate(fresh_database)
    db.migrate(fresh_database)
    with psycopg.connect(fresh_database) as conn:
        rows = conn.execute("select step from schema_steps order by step").fetchall()
    assert [r[0] for r in rows] == sorted({r[0] for r in rows})
    assert len(rows) == len(db.known_steps())


def test_migrate_keeps_existing_data(fresh_database):
    db.migrate(fresh_database)
    with psycopg.connect(fresh_database) as conn:
        conn.execute(
            "insert into models(model_key, model_id, first_imported_at) values ('a/b','A/b', now())"
        )
        conn.commit()
    db.migrate(fresh_database)
    with psycopg.connect(fresh_database) as conn:
        assert conn.execute("select count(*) from models").fetchone()[0] == 1


def test_a_database_newer_than_the_code_is_refused(fresh_database):
    db.migrate(fresh_database)
    with psycopg.connect(fresh_database) as conn:
        conn.execute("insert into schema_steps(step, applied_at) values (9999, now())")
        conn.commit()
    with pytest.raises(db.DatabaseTooNew):
        db.migrate(fresh_database)


def test_two_copies_starting_together_apply_each_step_once(fresh_database):
    errors = []

    def go():
        try:
            db.migrate(fresh_database)
        except Exception as exc:  # noqa: BLE001 - the test reports any failure
            errors.append(exc)

    threads = [threading.Thread(target=go) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    with psycopg.connect(fresh_database) as conn:
        assert conn.execute("select count(*) from schema_steps").fetchone()[0] == len(
            db.known_steps()
        )


def test_the_extensions_the_search_needs_are_installed(fresh_database):
    db.migrate(fresh_database)
    with psycopg.connect(fresh_database) as conn:
        names = {r[0] for r in conn.execute("select extname from pg_extension").fetchall()}
    assert "pg_trgm" in names


def test_the_runtime_role_can_read_and_insert_the_trail_but_not_change_it(fresh_database):
    db.migrate(fresh_database)
    db.apply_grants(fresh_database, role="catalog_rw", password=PW1)
    base, _, name = fresh_database.rpartition("/")
    host = base.split("@", 1)[1]
    url = f"postgresql://catalog_rw:{PW1}@{host}/{name}"
    with psycopg.connect(url) as conn:
        conn.execute(
            "insert into import_records(record_id, model_key, model_id, commit, imported_by_id, "
            "imported_by_name, imported_at, computer, bundle_name, bundle_sha256, "
            "signing_key_fingerprint, tool_version, check_results, outcome) values "
            "(gen_random_uuid(), 'a/b','a/b','c','u','n', now(),'pc','b','s','f','1','{}','imported')"
        )
        conn.commit()
        assert conn.execute("select count(*) from import_records").fetchone()[0] == 1
        for sql in ("update import_records set computer = 'x'", "delete from import_records"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(sql)
            conn.rollback()


def test_the_runtime_role_cannot_create_tables_or_reach_other_schemas(fresh_database):
    db.migrate(fresh_database)
    db.apply_grants(fresh_database, role="catalog_rw2", password=PW2)
    base, _, name = fresh_database.rpartition("/")
    host = base.split("@", 1)[1]
    url = f"postgresql://catalog_rw2:{PW2}@{host}/{name}"
    with psycopg.connect(url) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("create table x (a int)")
        conn.rollback()
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("create extension if not exists hstore")
