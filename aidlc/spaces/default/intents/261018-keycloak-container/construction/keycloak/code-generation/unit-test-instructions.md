# Unit Test Instructions: keycloak

## Test framework

`pytest` (already configured in the project). Tests first, then the file that makes them pass, then tidy up (the team's rule).

## Commands for this unit only

- Realm, compose, wiring, guide, pack and CI checks (no Docker needed): `.venv/bin/python -m pytest tests/test_keycloak_files.py -q`
- Real Keycloak sign-in tests (Docker and Google Chrome needed; skip cleanly where either is missing): `.venv/bin/python -m pytest server/e2e/tests/test_real_keycloak.py -q --timeout=300`

## Tests (Standard strategy: five to eight per component)

| Component | Tests | File |
|---|---|---|
| RealmDefinition | realm and role names; portal client flow, proof key, redirects, audience mapper; service client flow and audience mapper; two test users and the administrator role; every secret marked as a test value; no real-looking secret | `tests/test_keycloak_files.py` |
| KeycloakContainer | exact image pin, no `latest`; only `127.0.0.1:8080` published; realm mounted and imported; development mode; health check; `docker compose config` reads it | `tests/test_keycloak_files.py` |
| TestStackWiring | secrets written from the realm file; issuer value; only the Artifactory stand-in started; guide lists every realm, role, client and claim; pack and its build never include Keycloak files | `tests/test_keycloak_files.py` |
| SignInVerification | Keycloak ready in time; Chrome sign-in as ordinary user and as administrator; admin screens open only for the administrator; personal token made; the import service's token accepted by the Catalog; CI job present | `server/e2e/tests/test_real_keycloak.py`, `tests/test_keycloak_files.py` |

## Coverage

The scope's floor is 80% line coverage. This unit adds almost no Python source (a few lines in `deploy/smoke/standins.py`), which its tests exercise; no coverage tool is configured in the project and the team set no percentage floor (`team.md`), so coverage is by requirement in the traceability file.

## Mocking and test data

No mocks for the real sign-in tests: the point is the real Keycloak. The test portal, Catalog and import service run in the test process as in the existing whole-stack test; the Artifactory stand-in stands for Artifactory. Test users, client ids and secrets come only from the realm file.
