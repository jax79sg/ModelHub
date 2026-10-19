# Cross-Unit Traceability

## Verdict

PASS: 26 of 26 requirement IDs (every `FR` and `NFR` in `requirements.md`) are covered with status OK by the unit's `traceability.json`, and every target file exists. The user-stories stage was skipped, so there are no `AC` IDs. Uncovered: none.

## Per-ID coverage

| ID | Owning unit | Target file | Verdict |
|---|---|---|---|
| FR1, FR1.1, FR1.2, FR1.3 | keycloak | deploy/keycloak/compose.keycloak.yaml | OK |
| FR2, FR2.1, FR2.2, FR2.3 | keycloak | deploy/keycloak/modelhub-realm.json | OK |
| FR3, FR3.1, FR3.2, FR3.3 | keycloak | deploy/keycloak/modelhub-realm.json | OK |
| FR4, FR4.1 | keycloak | deploy/keycloak/modelhub-realm.json | OK |
| FR5 | keycloak | deploy/keycloak/up.sh | OK |
| FR5.1 | keycloak | deploy/keycloak/compose.stack.yaml | OK |
| FR5.2 | keycloak | deploy/keycloak/README.md | OK |
| FR6, FR6.2 | keycloak | server/e2e/tests/test_real_keycloak.py | OK |
| FR6.1 | keycloak | tests/test_keycloak_files.py | OK |
| FR6.3 | keycloak | .github/workflows/ci.yml | OK |
| NFR1, NFR2, NFR5 | keycloak | tests/test_keycloak_files.py | OK |
| NFR3 | keycloak | server/e2e/tests/test_real_keycloak.py | OK |
| NFR4 | keycloak | deploy/keycloak/compose.keycloak.yaml | OK |
