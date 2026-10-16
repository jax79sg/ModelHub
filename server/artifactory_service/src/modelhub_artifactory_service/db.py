"""The service's own schema and its upgrade steps (rule BR1.21, NFR4.5, NFR5.7).

Same discipline as the Catalog's: numbered steps applied under a lock, each recorded once,
existing data kept, a database newer than the code refused. The tables live in their own schema,
and the runtime role can reach only that schema.
"""

from __future__ import annotations

import re
from importlib import resources

import psycopg
from psycopg import sql

SCHEMA = "artifactory_service"
LOCK_KEY = 7_340_002
POOL_OPTIONS = f"-c search_path={SCHEMA} -c timezone=UTC"


class DatabaseTooNew(Exception):
    """The database holds an upgrade step this version of the service does not know."""


def known_steps() -> dict[int, str]:
    steps: dict[int, str] = {}
    folder = resources.files("modelhub_artifactory_service").joinpath("migrations")
    for entry in folder.iterdir():
        match = re.match(r"^(\d{4})_.*\.sql$", entry.name)
        if match:
            steps[int(match.group(1))] = entry.read_text("utf-8")
    return dict(sorted(steps.items()))


def migrate(url: str) -> list[int]:
    steps = known_steps()
    applied: list[int] = []
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("select pg_advisory_lock(%s)", (LOCK_KEY,))
        try:
            conn.execute(sql.SQL("create schema if not exists {}").format(sql.Identifier(SCHEMA)))
            conn.execute(sql.SQL("set search_path to {}").format(sql.Identifier(SCHEMA)))
            conn.execute(
                "create table if not exists schema_steps "
                "(step integer primary key, applied_at timestamptz not null)"
            )
            done = {r[0] for r in conn.execute("select step from schema_steps").fetchall()}
            unknown = done - set(steps)
            if unknown:
                raise DatabaseTooNew(
                    f"the database holds upgrade steps this version does not know: {sorted(unknown)}"
                )
            for number, text in steps.items():
                if number in done:
                    continue
                with conn.transaction():
                    conn.execute(text)
                    conn.execute(
                        "insert into schema_steps(step, applied_at) values (%s, now())", (number,)
                    )
                applied.append(number)
        finally:
            conn.execute("select pg_advisory_unlock(%s)", (LOCK_KEY,))
    return applied


def apply_grants(url: str, role: str, password: str) -> None:
    """Make the runtime role: it reaches only this service's schema, nothing else."""
    ident, schema = sql.Identifier(role), sql.Identifier(SCHEMA)
    with psycopg.connect(url, autocommit=True) as conn:
        exists = conn.execute("select 1 from pg_roles where rolname = %s", (role,)).fetchone()
        verb = "alter" if exists else "create"
        suffix = "" if exists else " login"
        conn.execute(
            sql.SQL(f"{verb} role {{}}{suffix} password {{}}").format(ident, sql.Literal(password))
        )
        db_name = conn.execute("select current_database()").fetchone()[0]
        conn.execute(sql.SQL("revoke all on schema public from {}").format(ident))
        conn.execute(
            sql.SQL("grant connect on database {} to {}").format(sql.Identifier(db_name), ident)
        )
        conn.execute(sql.SQL("grant usage on schema {} to {}").format(schema, ident))
        conn.execute(
            sql.SQL("grant select, insert, update, delete on all tables in schema {} to {}").format(
                schema, ident
            )
        )
        conn.execute(sql.SQL("revoke all on {}.schema_steps from {}").format(schema, ident))
        conn.execute(sql.SQL("grant select on {}.schema_steps to {}").format(schema, ident))


def make_pool(url: str, size: int = 10, statement_timeout_ms: int = 5000):
    """A connection pool whose connections see only this service's schema."""
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    return ConnectionPool(
        url,
        min_size=1,
        max_size=size,
        timeout=5,
        kwargs={
            "row_factory": dict_row,
            "options": f"{POOL_OPTIONS} -c statement_timeout={statement_timeout_ms}",
        },
        open=True,
    )
