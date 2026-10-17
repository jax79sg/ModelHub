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

154 tests in `server/artifactory_service/tests/`, re-run for this replay, including an end-to-end test of the program's own import client against this service.

## Deviations from the plan

The plan-decision change above. This record was also written afterwards, in a replay through the engine; the unit was built earlier without it (see the stage diary).
