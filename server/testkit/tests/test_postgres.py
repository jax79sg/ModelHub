"""The PostgreSQL fixture gives every test its own empty database (BQ2)."""

import psycopg


def test_each_test_gets_an_empty_database(fresh_database):
    with psycopg.connect(fresh_database) as conn:
        tables = conn.execute(
            "select count(*) from information_schema.tables where table_schema = 'public'"
        ).fetchone()[0]
        assert tables == 0
        conn.execute("create table t (x int)")
        conn.commit()


def test_a_second_test_does_not_see_the_first_tests_table(fresh_database):
    with psycopg.connect(fresh_database) as conn:
        found = conn.execute("select to_regclass('public.t')").fetchone()[0]
        assert found is None


def test_the_server_is_the_version_the_design_names(fresh_database):
    with psycopg.connect(fresh_database) as conn:
        version = conn.execute("show server_version_num").fetchone()[0]
        assert int(version) // 10000 >= 16


def test_the_extensions_the_design_needs_can_be_created(fresh_database):
    with psycopg.connect(fresh_database, autocommit=True) as conn:
        conn.execute("create extension if not exists pg_trgm")
        row = conn.execute("select 'tinyllama-gguf' % 'tinyllam'").fetchone()
        assert row is not None
