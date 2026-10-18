# Integration Test Instructions

## Boundaries and how to run them

| Boundary | Command | Needs |
|---|---|---|
| CLI import against the real service, Catalog and Artifactory stand-in | `.venv/bin/python -m pytest server/artifactory_service/tests/test_cli_end_to_end.py -q` | Docker (PostgreSQL) |
| Whole stack on real ports: sign-in, token, real import, portal | `.venv/bin/python -m pytest server/e2e -q --timeout=300` | Docker (PostgreSQL) |
| Portal against the real Catalog and a fake Keycloak | `.venv/bin/python -m pytest server/portal -q` | Docker (PostgreSQL) |
| Image build, scan, Compose smoke test and upgrade-and-return rehearsal | CI `images` job; locally `FROM=<tag> deploy/smoke/run.sh` | Docker host |

## Test data and environment

Bundles are made at run time with the program's own bundling code; tokens and secrets are generated; the stand-ins are started by the tests. Nothing reaches the internet.

## Coverage targets

Standard strategy: key boundary tests and cross-unit interaction. The whole-stack check and the smoke test cover the cross-unit path (sign-in, token, import, record, list, upgrade, return).

## Not covered

Anything that needs a real Artifactory, a real Keycloak, a real certificate or a browser is not exercised; see the Unverified rows of the Target Verification Matrix.
