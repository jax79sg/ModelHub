"""Database upgrade steps and access rights (rule BR1.21, NFR4.5, NFR5.3).

Steps are numbered files in ``migrations/``. They run in order under a database lock, each is
recorded once, existing data is kept, and a database that holds a step this code does not know
is refused.
"""

from __future__ import annotations

import re
from importlib import resources

import psycopg
from psycopg import sql

LOCK_KEY = 7_340_001  # one advisory lock for "the Catalog is changing its tables"


class DatabaseTooNew(Exception):
    """The database holds an upgrade step this version of the Catalog does not know."""


def known_steps() -> dict[int, str]:
    steps: dict[int, str] = {}
    folder = resources.files("modelhub_catalog").joinpath("migrations")
    for entry in folder.iterdir():
        match = re.match(r"^(\d{4})_.*\.sql$", entry.name)
        if match:
            steps[int(match.group(1))] = entry.read_text("utf-8")
    return dict(sorted(steps.items()))


def migrate(url: str) -> list[int]:
    """Apply pending steps. Returns the steps applied by this call."""
    steps = known_steps()
    applied: list[int] = []
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("select pg_advisory_lock(%s)", (LOCK_KEY,))
        try:
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
    """Make the runtime role: reads and writes its own tables, only inserts into the trail.

    The role is not a superuser, cannot create objects and cannot update or delete import
    records (the trail is only ever added to, rule BR1.13).
    """
    ident = sql.Identifier(role)
    with psycopg.connect(url, autocommit=True) as conn:
        exists = conn.execute("select 1 from pg_roles where rolname = %s", (role,)).fetchone()
        if not exists:
            conn.execute(
                sql.SQL("create role {} login password {}").format(ident, sql.Literal(password))
            )
        else:
            conn.execute(sql.SQL("alter role {} password {}").format(ident, sql.Literal(password)))
        conn.execute(sql.SQL("revoke all on schema public from {}").format(ident))
        db_name = conn.execute("select current_database()").fetchone()[0]
        conn.execute(
            sql.SQL("grant connect on database {} to {}").format(sql.Identifier(db_name), ident)
        )
        conn.execute(sql.SQL("grant usage on schema public to {}").format(ident))
        conn.execute(
            sql.SQL(
                "grant select, insert, update, delete on all tables in schema public to {}"
            ).format(ident)
        )
        conn.execute(sql.SQL("revoke update, delete on import_records from {}").format(ident))
        conn.execute(sql.SQL("revoke all on schema_steps from {}").format(ident))
        conn.execute(sql.SQL("grant select on schema_steps to {}").format(ident))
