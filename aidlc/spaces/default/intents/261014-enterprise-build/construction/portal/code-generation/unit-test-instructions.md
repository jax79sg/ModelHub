# Unit Test Instructions: portal

## Run this unit's tests

```bash
.venv/bin/python -m pytest server/portal -q --timeout=300
```

Scoped to this unit only. Install first: `pip install -e web -e server/testkit -e server/common -e server/catalog -e server/portal`. The tests need PostgreSQL (a `postgres:16` container started through Docker, or `MODELHUB_TEST_POSTGRES_URL`).

## Test framework and configuration

- pytest, tests in `server/portal/tests/`, written before the code (TDD, team practice).
- Real boundaries: the real Catalog app on a fresh PostgreSQL database per test, reached the way the portal reaches it; Keycloak is a fake sign-in (`server/testkit` `FakeKeycloak`) behind an httpx mock transport; the retention service is a small stand-in for the C4 routes.

## Coverage targets

Standard strategy: five to eight tests per component plus integration at the Catalog, Keycloak and service boundaries; the existing 83 tests stay green, and the whole-stack check (`server/e2e`) exercises the portal on real ports.

## Mocking and stubbing

Only the two outside systems are faked (Keycloak and the retention service); time is injected for session and token expiry.

## Test data

Versions are put into the real Catalog by a helper that mirrors the import service's calls; token values and secrets are generated at run time.
