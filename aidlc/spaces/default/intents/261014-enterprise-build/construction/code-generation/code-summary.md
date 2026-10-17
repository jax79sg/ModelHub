# Code Summary: enterprise build

## What was built

The seven units of the approved design, built inline in this order, each as its own pull request (all merged unless marked open):

| Unit | Where | Pull request |
|---|---|---|
| common (token check, guard, config, secrets, logs, health) | `server/common` | #10 |
| artifactory-stand-in (test-only Artifactory) | `server/stand_in` | #11 |
| catalog (schema, store, API) | `server/catalog` | #12 |
| artifactory-service (importer, jobs, API, retention, keys) | `server/artifactory_service` | #13 |
| portal (sign-in, sessions, list, model pages, tokens) | `server/portal`, reusing `web/` styles and sanitiser | #14 |
| import-cli (`login`, `logout`, `import`) | `src/modelhub/importer.py`, `settings.py`, `cli.py` | #15 |
| platform (images, Compose, proxy, operator guide) | `deploy/` | #16 |
| portal admin screens, trail, files, commits; signed server pack, smoke test, rehearsal; widening | `server/portal`, `deploy/`, `src/modelhub/serverpack.py` | #17, #18, #19, #20 (open) |

Test helpers (never shipped): `server/testkit` (fake sign-in, PostgreSQL fixture, bundle builder). Whole-stack check: `server/e2e`.

## Key implementation decisions

- **Plan decision for an import.** The signed bundle description does not list the files; the file manifest is inside the archive. So at create, if the Catalog already holds the version as imported, its recorded files are compared with Artifactory (complete: skip, absent: repair, different: fail); otherwise the plan stays `pending` and is decided after unpacking from the bundle's own manifest (complete: finish, absent: full, different: fail). This deviates from the design, which assumed a signed file list at create.
- **Pieces are consumed as they are read** (a reader subclass of the CLI's `JoinedPieces` deletes each piece), so disk use stays near one copy of the model.
- **The CLI's own code is reused by the service** through small compatible hooks: `verify_bundle(trusted=, only=)`, a public `rebuild_into`, `parse_public_doc`, `fingerprints_match`.
- **Personal tokens** are checked by the service through the Catalog's introspection; the guard in `common` gained `open_prefixes` so the import routes skip the Keycloak check and do their own.
- **Portal sign-in** uses Authlib only for the proof key and address building; calls to Keycloak are plain `httpx` (Authlib's own client switches to `httpx2` when installed). The id token's nonce, audience and issuer are checked.
- **The portal is a new package** (`server/portal`) that reuses the prototype's stylesheet, scripts, sanitiser and formatters from `web/`; the prototype and its 24 tests are unchanged.
- **Database roles.** A separate migration role makes the tables and the limited running roles; the services run as roles that cannot create objects, and the import service's role sees only its own schema.
- **Images** disable Xet transfers and telemetry; the proxy uses the nginx project's unprivileged image with the operating-system fixes applied.
- **The server pack** is a checksum list signed like a bundle (`modelhub pack sign|verify`).

## Test coverage summary

Counts at the last full run: CLI 445, common 90, catalog 125, import service 154, portal 83, stand-in 86, test helpers 15, whole-stack 1, plus the CI image job (build, scan, stand-in absence, non-root, secret-in-environment check, Compose smoke test, upgrade-and-return rehearsal). Every requirement is mapped to its checks in `docs/traceability.md`, with the gaps named. Tests were written before the code for each unit (red, then green), as the team practice says; a few bugs were found by the tests only after the first implementation (for example an empty missing-piece list treated as absent).

## Deviations from the plan

- The plan's step 8 (whole-stack check) was built as a real-port check in `server/e2e` and again as the Docker smoke test in CI.
- The rehearsal retags the same images as the "new" release, so it proves the procedure and that data survives, not a schema change.
- The migration step adds `MODELHUB_MIGRATION_USER`; the design's "migration role" had no code until then.
- Not built: importing an old model-store folder (reserved, exit 2), backup, and anything that needs a real Artifactory or Keycloak (the stand-in register lists what to confirm).

## Open items

- Run the stand-in register's checklist against a real Artifactory; confirm the `jf` command shape and repository layout.
- Keycloak clients and role, Artifactory repository and service account, TLS certificate, and the three signing secrets must be provided by their owners.
