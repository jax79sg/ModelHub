# Code Summary: portal

## What was built

The portal, built and merged before this replay (PRs #14, #17, #18).

- `oidc.py`, `sessions.py`, `app.py` - sign-in (authorisation code with a proof key, state and nonce checked against the id token), server-side sessions (8 idle hours, refresh before expiry), the default-deny gate, form tokens and the origin check, security headers.
- `catalog_client.py`, `service_client.py` - the Catalog and retention-service calls, always with the person's own token.
- Pages: models list, model, files, file, commits, trail (imports plus retention decisions), personal tokens, retention and trusted keys for administrators.
- `main.py` - start-up from settings and the sign-in secret file.

## Key decisions

- A new package that reuses the prototype's stylesheet, sanitiser and formatters from `web/`; the prototype and its 24 tests are unchanged.
- Authlib supplies only the proof key and address building; calls to Keycloak are plain `httpx` (Authlib's own client switches to `httpx2` when installed).
- No route serves a model file; a file's page shows its record and a fetch snippet only.

## Test coverage summary

83 tests in `server/portal/tests/` against the real Catalog on PostgreSQL, re-run for this replay, and the whole-stack check on real ports.

## Loop-back 2

Build and Test left seven portal targets Unverified; six are now checked by nine tests in `server/portal/tests/test_limits.py` (portal suite: 92 passed), with 1,000 models written into the real Catalog by a new helper `server/testkit/src/modelhub_testkit/catalog_data.py`. 95 of 100 list requests under 1 s (NFR2.1); the model page 95th percentile under 1 s (NFR2.2); four pages (list, model, files, tokens) weigh under 300 KB with their style and script and load nothing from outside (NFR2.3); sign-in redirect and callback each under 500 ms at the 95th percentile on the portal's side with the identity provider imitated in process (NFR2.4); 20 callers at once keep the list target (NFR7.1); a signed-in visit with every non-local socket blocked works (NFR8.1). These checks found no defect: the portal already met these targets, so the tests are guards. Still Unverified and named: NFR10.1 Chrome, Edge and Firefox (needs real browsers). No target was weakened.

## Deviations from the plan

None for the unit. This record was written afterwards, in a replay through the engine; the unit was built earlier without it (see the stage diary).
