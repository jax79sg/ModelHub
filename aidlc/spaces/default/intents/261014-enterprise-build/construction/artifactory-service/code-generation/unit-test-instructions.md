# Unit Test Instructions: artifactory-service

## Run this unit's tests

```bash
.venv/bin/python -m pytest server/artifactory_service -q --timeout=300
```

Scoped to this unit only. Install first: `pip install -e . -e server/testkit -e server/common -e server/catalog -e server/stand_in -e server/artifactory_service`. The tests need PostgreSQL (a `postgres:16` container started through Docker, or `MODELHUB_TEST_POSTGRES_URL`).

## Test framework and configuration

- pytest, tests in `server/artifactory_service/tests/`, written before the code (TDD, team practice).
- Real boundaries: a fresh PostgreSQL database per test, the real Catalog app on the same database, the Artifactory stand-in on a real local port, and signed bundles made by the program's own bundling code (`server/testkit` `make_bundle`).

## Coverage targets

Standard strategy: five to eight tests per component plus integration tests at the database, token, Catalog and stand-in boundaries; the existing 154 tests stay green. The end-to-end test drives the program's own import client against this service.

## Mocking and stubbing

Mocks only for things that cannot fail on purpose otherwise: a flaky uploader, a fake clock and sleep for retry waits, an injected disk-space function. Everything else is the real thing.

## Test data

Bundles are built at run time; tokens and secrets are generated with `uuid`, never fixed strings.
