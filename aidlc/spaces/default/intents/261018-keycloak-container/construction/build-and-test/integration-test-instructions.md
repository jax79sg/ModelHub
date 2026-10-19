# Integration Test Instructions

## Boundaries and how to run them

| Boundary | Command | Needs |
|---|---|---|
| Real Keycloak with the portal, Catalog and import service (sign-in in Chrome, personal token, the import service's own token, ready in time, no route out) | `.venv/bin/python -m pytest server/e2e/tests/test_real_keycloak.py -q --timeout=400` | Docker, Google Chrome, Playwright, PostgreSQL |
| Merged compose files read by Docker Compose | `.venv/bin/python -m pytest tests/test_keycloak_files.py -q` | Docker (skips without it) |
| Whole stack with the sign-in imitation (unchanged) | `.venv/bin/python -m pytest server/e2e -q --timeout=400` | Docker, PostgreSQL |
| CI | the job `keycloak (real sign-in)`; it fails if the tests were skipped | the runner's Docker and Chrome |

## Test data and environment

Test users, client ids and secrets come only from `deploy/keycloak/modelhub-realm.json`. The Keycloak container is started and removed by the tests. The Artifactory stand-in stands for Artifactory.

## Coverage targets

Standard strategy: key boundary tests. The scope's 80% line floor is read as: every executable line of new Python source is run by a test (21 of 21 lines of `deploy/smoke/standins.py` under the standard library's `trace`); no coverage tool is configured and `team.md` sets no percentage floor.

## Not covered

A Keycloak other than 26.8.1; the organisation's own Keycloak; production hardening (out of scope).
