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

## Loop-back 2

Build and Test left three common targets Unverified; they are now checked by three tests in `server/common/tests/test_limits.py`: a token check with a cached key under 5 ms at the 95th percentile over 300 checks (NFR5.9), the library working with every non-local socket blocked (NFR8.1), and a new `.github/dependabot.yml` covering the root package, each of the six server packages, the workflows and the image recipe, with a test that every package folder is listed (NFR5.11). Dependabot being switched on in the repository settings is not something a file proves; the file does. No target was weakened.

## Deviations from the plan

None for the unit. This record was written afterwards, in a replay through the engine; the unit was built earlier without it (see the stage diary).
