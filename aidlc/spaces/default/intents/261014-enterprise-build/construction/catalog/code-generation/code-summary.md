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

## Loop-back 2

Build and Test left 16 catalog targets Unverified; 13 are now checked by 29 tests in `server/catalog/tests/test_limits_and_events.py` (catalog suite: 154 passed). Real defects the checks found and this loop-back fixed: (1) `record_conflict` and `migration_applied` were never logged, now they are (NFR6.5, all six codes tested); (2) with the database away the service answered 500 instead of 503, now `psycopg.OperationalError` and pool timeouts give 503 `database_unavailable` and `/healthz` stays 200 (NFR4.3); (3) a connection the database dropped was handed out again, now the pool checks a connection on checkout and gives up reconnect attempts after 30 seconds so a request starts them again, tested with a relay that switches the database off and on; (4) `uvicorn` now runs with a 30 second stop grace (NFR4.4), and a store cut off part-way (backend killed) leaves no row in any table. Also checked: 95 of 100 list requests under 1 s at 1,000 models and 10,000 versions with 20 callers at once (NFR2.1, NFR7.1, NFR7.3); a list reads only `model_summary` (NFR2.2); one model or version under 300 ms at the 95th percentile (NFR2.4); first byte of a 16 MiB document under 1 s (NFR2.5); a version of 10,000 files and 64 MiB of documents stored under 60 s and an identical repeat under 1 s (NFR4.1); a second copy started on the same database (NFR7.4); hostile text in all 14 filters and in paths (NFR5.7); no outside connection (NFR8.1). Open point for the person: NFR4.1 says 100 MB of documents but NFR7.5 (and the code) refuse more than 64 MiB per version, so the test uses the largest accepted version; 100 MB cannot be stored by design. Still Unverified and owned elsewhere: NFR6.3 error-rate measure and NFR6.4 alert thresholds (monitoring team), NFR7.2 the 100 GB size plan (real system). No target was weakened.

## Deviations from the plan

None for the unit. This record was written afterwards, in a replay through the engine; the unit was built earlier without it (see the stage diary).
