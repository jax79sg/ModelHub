# Unit Test Instructions: common

## Run this unit's tests

```bash
.venv/bin/python -m pytest server/common -q --timeout=240
```

Scoped to this unit only. Install first: `pip install -e server/testkit -e server/common`.

## Test framework and configuration

- pytest, tests in `server/common/tests/`, written before the code (TDD, team practice).
- The fake Keycloak issuer from `server/testkit` mints valid, expired, tampered, wrong-audience, wrong-algorithm and unknown-key tokens, so no real Keycloak is needed.

## Coverage targets

Standard strategy: five to eight tests per component plus integration tests for the boundaries (the guard with a real app); the existing 90 tests stay green. No percentage floor is set by the team.

## Mocking and stubbing

No network mocks: the issuer is a real signer and serves a real key set. Time is injected where expiry is tested.

## Test data

Tokens are generated at run time; no fixed password-like strings are committed (they trip secret scanning).
