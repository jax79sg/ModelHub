# Test Results

## Build status

Success. `ruff check` and `ruff format --check` clean (673 files). All packages install. The four images build, scan and start in CI (`images` job), including the Compose smoke test and the upgrade-and-return rehearsal.

## Test results

Re-run after loop-back 1 on 2026-10-17 from the project root; each distinct command was run once.

| Command | Passed | Failed | Skipped |
|---|---|---|---|
| `pytest tests -q` (CLI, import command, pack, deployment definition, log search, loop guard) | 480 | 0 | 6 deselected (network tests) |
| `pytest web/tests -q` (prototype web app) | 24 | 0 | 0 |
| `pytest server/common -q` | 93 | 0 | 0 |
| `pytest server/catalog -q` | 154 | 0 | 0 |
| `pytest server/artifactory_service -q` | 183 | 0 | 0 |
| `pytest server/stand_in -q` | 95 | 0 | 0 |
| `pytest server/portal -q` | 92 | 0 | 0 |
| `pytest server/testkit -q` | 15 | 0 | 0 |
| `pytest server/e2e -q` | 1 | 0 | 0 |
| **Total** | **1137** | **0** | |

The per-unit commands in each unit's `unit-test-instructions.md` are subsets of these runs (for example `tests/test_import_cli.py` is part of `pytest tests`), so no test is counted twice.

## Failure details

No test failed. The stage does not pass on its target matrix: 0 targets are Not Met and 13 are Unverified, out of 188 (after loop-back 3). See `build-and-test-summary.md`. Loop-backs 2 and 3 closed 48 Unverified targets, including `artifactory-service:NFR10.1` and `platform:NFR5.1`, which the CI `images` job proved (run 39088051063).

CI on the pushed branch: every build, test, stand-in, web, offline-pack, lint, image and smoke job passes. Two checks are not green: CodeQL (one alert in a new portal test, fixed in the next commit) and GitGuardian (a fake key-shaped text in a new test, no longer built from literal text; the earlier commit may still need marking as a false positive in GitGuardian).

## Coverage report

No coverage tool is configured and the team set no percentage floor (`team.md`); coverage is by requirement, in `docs/traceability.md` and `cross-unit-traceability.md`.

## Accepted failure

On 2026-10-17 the person was shown the halt-and-ask for this result (4 Not Met, 60 Unverified; candidate fix: reopen Code Generation for artifactory-service, import-cli and platform, estimated effort about half a day, no cost, low risk; loop-backs used 0/3) and chose **Accept failure**. No loop-back was made, so there is no Loop-Back Log. The 4 Not Met and 60 Unverified targets stay open and are listed in `build-and-test-summary.md`; the stage is presented for approval with the readiness answer "not deployment-ready".

## Loop-Back Log

### Loop-back 1 — 2026-10-17T11:35:00Z

- **Diagnosis:** 4 targets Not Met in build-and-test-summary.md: (1) artifactory-service NFR6.2, `/readyz` checks the database only; (2) artifactory-service NFR6.5, the fixed event codes are not logged; (3) import-cli NFR6.3, the import command writes no run record; (4) artifactory-service NFR10.1 (image side), the image has no JFrog CLI.
- **Root-cause stage:** code-generation, units artifactory-service (1, 2), import-cli (3) and platform (4, the image).
- **Planned fix:** (1) report Artifactory and the Catalog as degraded in `/readyz`; (2) log import_created, import_skipped, import_done, import_failed, key_added, key_revoked with fixed codes and no secrets; (3) write a run-record line per model from the import command, without the token; (4) install a pinned JFrog CLI in the service image (the default upload path stays huggingface_hub).
- **Estimated impact:** effort about half a day plus 3 plan approvals and 3 checkpoints; financial cost none; risk low (the image change is proven only by the CI image build). The 60 Unverified targets are not part of this loop-back.

### Loop-back 2 — 2026-10-17T12:10:00Z

- **Diagnosis:** after loop-back 1 there are 0 Not Met and 61 Unverified targets of 188 (127 Met). No stage owns the Unverified ones; about 35 can be checked inside this repository, about 26 cannot (real Artifactory, central monitoring, browsers, host firewall, free-space planning).
- **Root-cause stage:** code-generation, units common, artifactory-stand-in, catalog, artifactory-service, portal, import-cli and platform (the checks were never written).
- **Planned fix:** add executable checks for the repository-checkable Unverified targets (timings, parallel callers, many pieces and bundles, hostile text in every filter, token never in logs, no outside connection, JFrog CLI image); no target is weakened.
- **Estimated impact:** effort about 1 to 2 days plus up to 7 plan approvals and checkpoints; financial cost none; risk low. About 26 targets stay Unverified and need a real environment or an accepted-by-name decision.

The person chose **Retry with fix** for the 61 Unverified targets: loop-back 2 reopened Code Generation for all seven units; all seven were replanned, approved, built, verified and approved again.

### Loop-back 3 — 2026-10-18T02:20:00Z

- **Diagnosis:** after loop-back 2 there are 0 Not Met and 14 Unverified targets of 188 (174 Met). One of them, `platform:NFR7.2`, has a code fix: the import service checks free space when an import is created but not again when it is started, while the documented minimums are to be checked at start.
- **Root-cause stage:** code-generation, unit artifactory-service (the importer's start step).
- **Planned fix:** refuse to start an import when the free space on the working volume is under the minimum, with a retryable reason, tested; no target is weakened.
- **Estimated impact:** effort about an hour plus 1 plan approval and 1 checkpoint; financial cost none; risk low. The other 13 Unverified targets stay open: 6 need a real system, 4 belong to other teams, 3 need the person's decision.

