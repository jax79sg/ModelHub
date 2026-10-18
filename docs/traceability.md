# Requirement-to-test table (enterprise server and import command)

Each requirement of the enterprise design (`aidlc/spaces/default/intents/261011-enterprise-modelhub/inception/requirements-analysis/requirements.md`)
with where it is built and which automated check proves it. Paths are relative to the repository root. "CI" means a job in
`.github/workflows/ci.yml`. Status is **covered** (a check fails if it breaks), **partly** (the check proves less than the whole
requirement; the gap is named) or **open** (nothing proves it yet).

Units: **common** `server/common`, **catalog** `server/catalog`, **service** `server/artifactory_service`, **portal** `server/portal`,
**CLI** `src/modelhub` (tests in `tests/`), **stand-in** `server/stand_in`, **platform** `deploy/`, **e2e** `server/e2e`.

## Importing (FR1)

| Req | Built in | Checked by | Status |
|---|---|---|---|
| FR1.1 verified package handed to the service | CLI `importer.py`; service `importer.py` | `tests/test_import_cli.py` (verify then send), `server/artifactory_service/tests/test_cli_end_to_end.py`, `server/e2e/tests/test_whole_stack.py` | covered |
| FR1.2 personal token checked with the Catalog; importer recorded | service `app.py` (`import_owner`), catalog tokens | `server/artifactory_service/tests/test_api.py` (token tests), `server/catalog/tests/test_api.py` | covered |
| FR1.3 record and trail row written in the same import | service `record_builder.py`, `importer.py`; catalog `store.py` | `server/artifactory_service/tests/test_pure.py`, `test_importer.py`, `server/catalog/tests/test_store_put.py` | covered |
| FR1.4 already imported is skipped | service plan at create | `test_importer.py` (skipped and trail), `tests/test_import_cli.py`, `test_cli_end_to_end.py` | covered |
| FR1.5 files present, record missing: finish without re-upload | service plan `finish` | `test_importer.py` (finished after unpacking) | covered |
| FR1.6 record present, files missing: upload again, keep record | service plan `repair` | `test_importer.py` (repaired), smoke rehearsal in CI | covered |
| FR1.7 names checked against Artifactory rules | service `names.py` | `test_pure.py`, `test_importer.py` (bad names) | covered |
| FR1.8 never overwrite; 409 fails the model | service `gateway.py` | `server/artifactory_service/tests/test_gateway.py`, `server/stand_in/tests` | covered |
| FR1.9 5 retries at 1, 2, 4, 8, 16 s with jitter | service `retry.py`; CLI `importer.py` | `test_pure.py` (retry), `test_importer.py` (flaky upload), `tests/test_import_cli.py` (retries, busy wait) | covered |
| FR1.10 exit status 0 / 1 / 2 | CLI `cli.py` | `tests/test_import_cli.py` | covered |
| FR1.11 report lists each model; no token printed | CLI `importer.py`, `redact.py` | `tests/test_import_cli.py` (report, secrecy) | covered |
| FR1.12 one import per model at a time | service lock | `test_importer.py` (model_locked, cancel frees) | covered |
| FR1.13 progress over 2 s | CLI `progress.py` | `tests/test_progress.py`, `tests/test_import_cli.py` (polling) | partly: the progress line itself is checked by the existing tests, not against a live import |
| FR1.14 signature and every file checked by the service | service `importer.py`, `keys.py` | `test_importer.py` (untrusted key, tampered description, damaged piece), `test_keys.py`, `test_api.py` | covered |

## Recording (FR2)

| Req | Built in | Checked by | Status |
|---|---|---|---|
| FR2.1 version fields | catalog schema; service `record_builder.py` | `server/catalog/tests/test_records.py`, `test_store_put.py`, `test_pure.py` | covered |
| FR2.2 README, pictures, responses, manifest, signed files stored | `record_builder.py`; catalog documents | `test_pure.py` (documents), `server/catalog/tests/test_store_read.py` | covered |
| FR2.3 one trail row per import | catalog `import_records` | `test_store_put.py` (one trail row, repeat adds none), `test_importer.py` (skip leaves a trail) | covered |
| FR2.4 not given means null, never 0 | catalog `records.py` | `test_store_put.py` (null versus zero), portal `tests/test_pages.py` (unknown, never 0) | covered |
| FR2.5 all written in one transaction | catalog `store.py` | `test_store_put.py` (a failure part way leaves nothing) | covered |
| FR2.6 unknown fields kept | catalog | `test_store_put.py` (unknown fields do not stop the store) | covered |
| FR2.7 licence and "no licence given" | catalog; portal | `test_store_put.py`, portal `tests/test_pages.py` | covered |
| FR2.8 no README / not downloaded / unfetched picture | `record_builder.py`; portal | `test_pure.py`, `test_store_put.py`, portal `tests/test_pages.py`, `test_more_pages.py` | covered |

## Portal (FR3) and access (FR4)

| Req | Built in | Checked by | Status |
|---|---|---|---|
| FR3.1 every page needs sign-in | portal `app.py` gate | `server/portal/tests/test_signin.py` (every closed path redirects) | covered |
| FR3.2 portal reads the database (via the Catalog) | portal `catalog_client.py` | all of `server/portal/tests/` run against the real Catalog | covered |
| FR3.3 list, filters, sort, paging, card, files, commits, revisions | portal | `test_pages.py`, `test_more_pages.py` | partly: the prototype's task/parameter range slider and "displayed" filter groups are simplified to chips |
| FR3.4 filter and sort by import time and importer | catalog filters; portal | `test_store_read.py`, portal `test_pages.py` (imported by, dates, sort) | covered |
| FR3.5 search the text of cards | catalog full-text | `server/catalog/tests/test_store_read.py` (search), portal `test_pages.py` | covered |
| FR3.6 fetch instructions, no file served | portal | `test_pages.py` (snippets, no file route), `test_more_pages.py` (no content) | covered |
| FR3.7 safe rendering | `hubsite.markdown` reused | `test_pages.py` (hostile card text, pictures as data, never svg) | covered |
| FR3.8 service down is said plainly | portal | `test_pages.py` (catalog down), `test_signin.py` (Keycloak down, expiry), `test_admin.py` (service down) | covered |
| FR4.1 every signed-in person can browse | portal | `test_pages.py` | covered |
| FR4.2 / FR4.3 administrator role; others refused | common `guard.py`; portal | `server/common/tests/test_guard.py`, `server/portal/tests/test_admin.py` | covered |
| FR4.4 make a token, value shown once, hash stored | catalog; portal | `server/catalog/tests/test_api.py`, portal `test_pages.py` (shown once, never logged) | covered |
| FR4.5 token works only for importing; expiry; revoke | catalog; service | `test_api.py` (catalog and service: personal token only under imports, revoked told to make a new one) | covered |
| FR4.6 own tokens listed without values; admin sees all | catalog; portal | `test_pages.py` (own versus all) | covered |

## Retention (FR5)

| Req | Built in | Checked by | Status |
|---|---|---|---|
| FR5.1 period setting, default 1 year | service `retention.py` | `server/artifactory_service/tests/test_retention.py`, `test_api.py` | covered |
| FR5.2 age from import time | `retention.py` | `test_retention.py` | covered |
| FR5.3 / FR5.4 due list; decision each time; keep restarts age | `retention.py`; portal `/admin/retention` | `test_retention.py`, portal `test_admin.py` | covered |
| FR5.5 remove deletes files then marks removed | `retention.py` | `test_retention.py` | covered |
| FR5.6 failed deletion leaves it listed and retryable | `retention.py` | `test_retention.py` (failed, files deleted but not marked) | covered |
| FR5.7 decisions part of the trail | service decisions; portal `/trail` | `test_retention.py`, portal `test_more_pages.py` (merged into the trail) | covered |

## Hosting (FR6)

| Req | Built in | Checked by | Status |
|---|---|---|---|
| FR6.1 Compose, one server | `deploy/compose.yaml` | `tests/test_deploy_definition.py`; CI `images` job (stack starts) | covered |
| FR6.2 images reach the server through the pack; nothing downloaded while running | `deploy/build-pack.sh`, `ops.sh load-images` | `tests/test_build_pack.py`, `tests/test_serverpack.py` | covered for the pack; the "no route to the internet" part is the host's firewall (documented, not tested) |
| FR6.3 database data survives restart and upgrade | `catalog-db` volume | CI rehearsal (`deploy/smoke/run.sh`) | covered |
| FR6.4 secrets in files only | `compose.yaml`, `ops.sh` | `tests/test_deploy_definition.py`; CI `images` job (no secret-looking environment value) | partly: AC6.1 also asks for a search of logs, which is checked for the Catalog token (`server/catalog/tests/test_api.py`) and the CLI, not for every container |
| FR6.5 JSON logs and health checks | common `logs.py`, `health.py` | `server/common/tests/`, compose health checks | covered |
| FR6.6 upgrade and return keep data | `deploy/README.md`, `smoke/run.sh` | CI rehearsal | covered (same images under a new tag; no schema change is exercised) |

## Stand-in (FR7) and old folders (FR8)

| Req | Built in | Checked by | Status |
|---|---|---|---|
| FR7.1 stand-in answers what the upload tools and libraries call | `server/stand_in` | `server/stand_in/tests/` (86) | covered |
| FR7.2 documented behaviours and an assumptions register | `assumptions.json`, `register.py` | `server/stand_in/tests/test_switches_and_register.py` | covered |
| FR7.3 checklist for a real Artifactory | `register.checklist_markdown()` | same | covered (running it against a real Artifactory is still to do) |
| FR8.1 import of an old model-store folder | reserved | `tests/test_import_cli.py` (`--from-store` says it is not available, exit 2) | open by design: built after the first version |

## Non-functional

| Req | Built in | Checked by | Status |
|---|---|---|---|
| NFR1 findable within an hour | whole path | `server/e2e/tests/test_whole_stack.py` | covered (immediately, not timed against an hour) |
| NFR2 list under 1 s at 1,000 models | catalog | `server/catalog/tests/test_list_speed.py` | covered |
| NFR3 availability in business hours | restart policy, health | `tests/test_deploy_definition.py` | covered as configuration |
| NFR4 restart gives a correct result | service sweeps; CLI resume | `test_importer.py` (idle, interrupted), `tests/test_import_cli.py` (rerun sends only missing pieces, Ctrl-C) | covered |
| NFR5 security | guard, sessions, forms, secrets | `test_guard.py`, `test_signin.py`, `test_admin.py`, `test_deploy_definition.py`, `tests/test_secrets.py`, `test_main.py` (limited database roles) | covered |
| NFR6 operability, one documented upgrade run | `deploy/README.md` | CI rehearsal; `/readyz` tests | covered |
| NFR7 capacity, memory at or below 8 GB | CLI streaming, service rebuild | `tests/test_memory_limits.py`, `tests/test_scale.py` | partly: the server side was not measured at 100 GB |
| NFR8 no internet while running | compose, pack | `tests/test_offline.py` (CLI), `tests/test_deploy_definition.py` | partly: container egress is the host firewall's job |
| NFR9 tests first, stand-in only | all units | the suites themselves | covered |
| NFR10 import behaves the same on Linux and Windows | CLI | CI `test` and `build-*` jobs on Linux, Windows and macOS; `tests/test_import_cli.py` | covered |

## Acceptance criteria

| AC | Checked by |
|---|---|
| AC1.1 to AC1.5 | `test_cli_end_to_end.py`, `test_importer.py` |
| AC1.6 | `test_importer.py` (bad names refused, others carry on via `tests/test_import_cli.py` damaged-bundle ordering) |
| AC1.7 | `test_gateway.py` |
| AC1.8 | `tests/test_import_cli.py`, `test_importer.py` |
| AC1.9 | `test_importer.py` (model_locked) |
| AC1.10 | `test_importer.py`, `test_api.py` |
| AC2.1 / AC2.2 | `test_store_put.py`; portal `test_pages.py` |
| AC3.1 | `test_signin.py` |
| AC3.2 / AC3.3 | catalog `test_store_read.py`; portal `test_pages.py` |
| AC3.4 / AC3.5 | portal `test_pages.py` |
| AC4.1 | `test_admin.py`, `test_guard.py` |
| AC4.2 / AC4.3 | service `test_api.py`; `test_whole_stack.py`; catalog `test_api.py` |
| AC5.1 / AC5.2 | `test_retention.py`, `test_admin.py` |
| AC6.1 | CI `images` job (environment), catalog log test; see FR6.4 |
| AC6.2 | CI rehearsal |
| AC7.1 | the CLI, service and whole-stack tests run with only the stand-in |
| NFR-AC1 | `test_list_speed.py` |

## What is not proven yet

- Nothing has run against a real Artifactory or Keycloak. The stand-in's register lists what to confirm (`python -m modelhub_stand_in --checklist`).
- The rehearsal does not include a database step that changes the schema.
- Backup and restore are out of scope by design.
