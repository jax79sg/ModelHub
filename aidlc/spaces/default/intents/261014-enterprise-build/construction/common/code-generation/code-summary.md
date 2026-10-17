# Code Summary: common

## What was built

The code every server-side unit needs, built and merged before this replay (PR #10), with later additions in PRs #14 and #19 (open path prefixes for the guard, the sign-in test double in `server/testkit`).

- `tokens.py`, `keys.py` - the Keycloak token check (RS256 and ES256 only, issuer, audience, expiry) and its key set with a limited refresh.
- `guard.py` - default-deny middleware, `/healthz` and `/readyz`, plain `{code, message}` errors, request ids, administrator and service-identity checks, open path prefixes.
- `config.py`, `secrets.py`, `logs.py`, `health.py` - settings and secret files with start-up errors that name every missing item and no value, JSON logs that redact secrets, the health registry.
- `server/testkit` - test helpers (fake issuer, PostgreSQL fixture, bundle builder, fake sign-in) that are never shipped.

## Key decisions

- Algorithms other than RS256 and ES256 are refused outright; a token never appears in a log or an error.
- Secrets come from files under `/run/secrets` and are wrapped so they cannot be printed by accident.

## Test coverage summary

90 tests in `server/common/tests/`, re-run for this replay. The test helpers have 15 of their own.

## Deviations from the plan

None for the unit. This record was written afterwards, in a replay through the engine; the unit was built earlier without it (see the stage diary).
