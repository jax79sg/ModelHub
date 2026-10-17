# Unit Test Instructions: catalog

## Run this unit's tests

```bash
.venv/bin/python -m pytest server/catalog -q --timeout=300
```

Scoped to this unit only. Install first: `pip install -e server/testkit -e server/common -e server/catalog`. The tests need PostgreSQL: they start a `postgres:16` container through Docker, or use the server named in `MODELHUB_TEST_POSTGRES_URL` (as CI does).

## Test framework and configuration

- pytest, tests in `server/catalog/tests/`, written before the code (TDD, team practice).
- A fresh database per test (the `fresh_database` fixture from `server/testkit`).
- Tokens come from the fake issuer in `server/testkit`.

## Coverage targets

Standard strategy: five to eight tests per component plus integration tests at the database and token boundaries; the existing 125 tests stay green. The list-speed check holds the median and 95th percentile under the 1 second target at 1,000 models.

## Mocking and stubbing

No database mocks: every store test runs against real PostgreSQL. Time is injected where expiry and last-used are tested.

## Test data

Records built by small helpers in `tests/conftest.py`; token values and secrets are generated at run time, never fixed strings.
