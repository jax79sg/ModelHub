# Test Results

## Build status

Success. `ruff check .` and `ruff format --check .` clean (725 files). The compose files read (`docker compose config`).

## Test results

Run on 2026-10-19 from the project root; each distinct command was run once.

| Command | Passed | Failed | Skipped |
|---|---|---|---|
| `pytest tests -q` (CLI, import command, pack, deployment definition, Keycloak files) | 515 | 0 | 6 deselected (network tests) |
| `pytest web/tests -q` | 24 | 0 | 0 |
| `pytest server/common -q` | 99 | 0 | 0 |
| `pytest server/catalog -q` | 154 | 0 | 0 |
| `pytest server/artifactory_service -q` | 183 | 0 | 0 |
| `pytest server/stand_in -q` | 95 | 0 | 0 |
| `pytest server/portal -q` | 92 | 0 | 0 |
| `pytest server/testkit -q` | 15 | 0 | 0 |
| `pytest server/e2e -q` (whole stack, Chrome, 8 real Keycloak tests) | 10 | 0 | 0 |
| **Total** | **1187** | **0** | |

The per-unit command for this unit (`tests/test_keycloak_files.py` and `server/e2e/tests/test_real_keycloak.py`) is a subset of these runs.

## Failure details

No test failed. Every target is Met.

## Coverage report

No coverage tool is configured and `team.md` sets no percentage floor; coverage is by requirement (`cross-unit-traceability.md`) and, for the one new Python source file, every executable line of `deploy/smoke/standins.py` is run by a test (21 of 21, standard library `trace`).

## CI

PR 30 (commit 09762bf and the one after): the job `keycloak (real sign-in)` ran 8 tests on Google Chrome 155 and passed; the other jobs are listed in the PR.
