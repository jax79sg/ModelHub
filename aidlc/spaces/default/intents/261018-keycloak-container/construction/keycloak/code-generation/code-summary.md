# Code Summary: keycloak

## What was built

- `deploy/keycloak/modelhub-realm.json`: the realm `modelhub`, role `modelhub-admin`, the portal client `modelhub` (confidential, code flow with a proof key, audience mapper), the import service client `modelhub-artifactory-service` (client credentials, audience mapper), and the test users `ada` and `root` (administrator). Every secret and password is marked as a test value.
- `deploy/keycloak/compose.keycloak.yaml`: one Keycloak from `quay.io/keycloak/keycloak:26.8.1` (pinned exactly) in development mode, realm imported at start, published only on `127.0.0.1:8080`, issuer `http://keycloak:8080/realms/modelhub`, a health check on the realm's discovery address.
- `deploy/keycloak/compose.stack.yaml` and `up.sh`: the whole stack beside it with only the Artifactory stand-in (`deploy/smoke/standins.py` takes `SIGNIN_STANDIN=0`); secrets come from the realm file.
- `deploy/keycloak/README.md`: how to start it, the test people, and the settings to copy into the organisation's Keycloak; a line in `deploy/README.md`.
- `server/e2e/tests/test_real_keycloak.py` (7 tests, real Keycloak, Chrome) and `tests/test_keycloak_files.py` (24 tests on the files); a CI job `keycloak (real sign-in)`; the pack build test forbids any `keycloak` file in the pack.

## Key decisions

- The issuer is the container's own name (`keycloak:8080`) so the stack needs no change; on a computer the name is mapped to 127.0.0.1 (hosts file, and inside the tests by a patched name lookup and Chrome's host-resolver rule). Chosen by the person (Q1).
- The portal's redirect address is added through Keycloak's admin interface in the test, because the test portal runs on a free port.
- Version 26.8.1 is the newest image on quay.io; Keycloak has no separate long-term-support line (Q2).

## Test coverage summary

`tests/test_keycloak_files.py`: 24 passed (no Docker needed except two compose-config checks, which skip without it). `server/e2e/tests/test_real_keycloak.py`: 7 passed against the real Keycloak in 32 s (ready within the 120 s limit). Full CLI suite 514 passed; ruff clean.

## What the real Keycloak taught (deviations from the first design)

- Keycloak rejected the realm file's `description` (not a realm field); it is now a realm `attributes.note` and the display name says TEST ONLY. Found by starting the real container, not by the file tests.
- The TDD red step for the real sign-in tests was the missing realm and compose files; once those existed the seven tests passed at the first run.
- The first token inspected carries `aud` (`modelhub`, `account`), `azp`, `preferred_username` and `realm_access`; the audience mapper works as designed.
