# Code Summary: artifactory-service

## What was built

The import service, built and merged before this replay (PR #13), widened in PRs #17 and #20.

- `db.py`, `migrations/0001_initial.sql` - the service's own schema and numbered step, the limited running role.
- `gateway.py`, `catalog_client.py` - the only caller of Artifactory (list with prefix discovery, delete, upload through `huggingface_hub` or `jf`), and the Catalog client with the service token.
- `importer.py`, `names.py`, `retry.py`, `record_builder.py` - the import jobs: names, signature against trusted keys, disk check, per-model lock, plan decision, pieces consumed as read, upload with retries, record, cancel, idle and restart sweeps.
- `retention.py`, `keys.py` - the retention period, due list, keep and two-step removal; the trusted keys.
- `app.py`, `main.py` - the C1 and C4 routes, personal-token check through the Catalog, the 426 rule, start-up from settings and secret files.
- Reused hooks in `src/modelhub/`: `verify_bundle(trusted=, only=)`, a public `rebuild_into`, `parse_public_doc`, `fingerprints_match`.

## Key decisions

- **Plan decision (deviation from the design).** The signed description does not list files; the file manifest is inside the archive. At create the Catalog's recorded files are compared with Artifactory when the version is already imported (skip, repair, fail); otherwise the plan stays pending and is decided after unpacking from the bundle's own manifest (finish, full, fail).
- A running import can be cancelled; it stops before unpacking or uploading and cleans up.
- The disk check is the sizes plus 10 percent and is retryable.

## Test coverage summary

167 tests in `server/artifactory_service/tests/` (154 re-run for the replay plus 13 added by loop-back 1), including an end-to-end test of the program's own import client against this service.

## Loop-back 1 (from Build and Test)

Build and Test found two targets of this unit Not Met and the person chose to fix them (tests first, then code):

- NFR6.2 - `/readyz` now reports Artifactory and the Catalog as `degraded` when they cannot be reached (they are never critical; only the database is). New `Gateway.ping()` (storage listing of the repository with the credential) and `CatalogClient.ping()` (the Catalog's live check, no token); wired in `main.py` through `extra_checks`. The Artifactory stand-in now answers the empty repository root with 200, as a real repository does.
- NFR6.5 - the fixed event codes `import_created`, `import_skipped`, `import_done`, `import_failed`, `import_cancelled`, `key_added`, `key_revoked` and `retention_decided` are logged with ids and codes only (no token, secret or raw Artifactory text).
- Tests: `tests/test_operability.py` (ping, readiness, each event, no secret in any event) and `tests/test_main.py` (degraded readiness through the real start-up).

## Loop-back 2

Build and Test left 15 import service targets Unverified; 9 are now checked by 15 tests in `server/artifactory_service/tests/test_limits_and_resilience.py` (service suite: 182 passed), using a new switch-off-and-on relay in `server/testkit/src/modelhub_testkit/relay.py`. Short calls at the 95th percentile under 1 s, alone and with 20 callers at once (NFR2.1, NFR7.7); a piece acknowledged with under 100 ms of overhead (NFR4.1); the service killed at each of five points (verifying, unpacking, before upload, after upload, before recording), failed as interrupted on restart and the import run again to a correct, complete result in Artifactory and the Catalog (NFR4.2); Artifactory away (real relay): the import fails as retryable, readiness says `degraded` while liveness stays 200, and the next import succeeds after it returns, and the same for the Catalog (NFR3.2); a 48 MiB import in 8 MiB pieces with traced memory below the bundle size (NFR7.3); the credential in no log at any level and, with a stand-in upload tool, in neither its process listing nor its arguments (NFR5.2); and a full import with every non-local socket blocked (NFR8.1). A real gap was found and fixed: the work folder and each import folder were made with the default mode, now they are owner-only (0700) (NFR5.5). Not done, on purpose: NFR9.2 asks for the Hugging Face library to be pinned to a release Artifactory supports (up to 1.19.0), but the service, the stand-in and the CLI are all built on `huggingface_hub>=2.2,<3`; changing that is a design decision for the person, not a test, so it stays Unverified and is flagged. Also still Unverified and named: NFR6.4 alert thresholds (monitoring team), NFR7.1 and NFR7.2 (100 GB import and disk speed need a real Artifactory), NFR7.6 free-space planning, NFR10.1 the JFrog CLI download until CI builds the image. No target was weakened.

## Deviations from the plan

The plan-decision change above. This record was also written afterwards, in a replay through the engine; the unit was built earlier without it (see the stage diary).
