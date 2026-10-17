# Code Summary: catalog

## What was built

The Catalog, built and merged before this replay (PR #12) and widened in PRs #13, #14, #17 and #20 (the retention and trail lists, the importer-name filter).

- `db.py`, `migrations/0001_initial.sql` - numbered steps under an advisory lock, the schema, the limited running role.
- `records.py`, `store.py` - validation, one-transaction storing of a version with files, documents, refs and its trail row; repeat and conflict rules; removal; the list that never reads documents; full-text search; facets; personal tokens (hashed, expiring, revocable, introspection).
- `app.py`, `main.py` - the C2 and C3 routes (reads for any signed-in person, writes for the import service's identity only), start-up from settings and secret files with an optional migration role.

## Key decisions

- The list reads one summary table only, so it stays fast at 1,000 models (3 ms median, 8 ms 95th percentile measured).
- Documents are served as data with a restrictive policy and are emptied when a version is removed; unsafe types are never served as themselves.
- A token's value is shown once and only a keyed hash is stored; it is never logged.

## Test coverage summary

125 tests in `server/catalog/tests/` on real PostgreSQL, re-run for this replay.

## Deviations from the plan

None for the unit. This record was written afterwards, in a replay through the engine; the unit was built earlier without it (see the stage diary).
