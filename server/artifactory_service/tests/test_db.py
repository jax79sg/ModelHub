"""The service's own schema and upgrade steps (rule BR1.21, NFR4.5, NFR5.7)."""

import threading
import uuid

import psycopg
import pytest
from modelhub_artifactory_service import db

PW = "p" + uuid.uuid4().hex


def tables(url, schema=db.SCHEMA):
    with psycopg.connect(url) as conn:
        rows = conn.execute(
            "select table_name from information_schema.tables where table_schema = %s", (schema,)
        ).fetchall()
    return {r[0] for r in rows}


def test_migrate_creates_the_tables_in_its_own_schema_only(fresh_database):
    db.migrate(fresh_database)
    assert {
        "import_jobs",
        "received_pieces",
        "model_locks",
        "trusted_keys",
        "retention_settings",
        "retention_decisions",
        "schema_steps",
    } <= tables(fresh_database)
    assert tables(fresh_database, "public") == set()


def test_migrate_twice_changes_nothing(fresh_database):
    first = db.migrate(fresh_database)
    assert first and db.migrate(fresh_database) == []


def test_a_database_newer_than_the_code_is_refused(fresh_database):
    db.migrate(fresh_database)
    with psycopg.connect(fresh_database) as conn:
        conn.execute(f"insert into {db.SCHEMA}.schema_steps(step, applied_at) values (9999, now())")
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
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors
    with psycopg.connect(fresh_database) as conn:
        n = conn.execute(f"select count(*) from {db.SCHEMA}.schema_steps").fetchone()[0]
    assert n == len(db.known_steps())


def test_the_runtime_role_reaches_only_its_own_schema(fresh_database):
    db.migrate(fresh_database)
    with psycopg.connect(fresh_database, autocommit=True) as conn:
        conn.execute("create table public.catalog_like (a int)")  # another service's table
    db.apply_grants(fresh_database, role="svc_rw", password=PW)
    base, _, name = fresh_database.rpartition("/")
    url = f"postgresql://svc_rw:{PW}@{base.split('@', 1)[1]}/{name}"
    with psycopg.connect(url, options=db.POOL_OPTIONS) as conn:
        conn.execute("select count(*) from import_jobs").fetchone()
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("select * from public.catalog_like")
        conn.rollback()
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("create table public.x (a int)")
        conn.rollback()
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("create table artifactory_service.x (a int)")
