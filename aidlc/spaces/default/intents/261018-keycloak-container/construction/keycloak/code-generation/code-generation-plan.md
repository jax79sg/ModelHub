# Code Generation Plan: keycloak

## Summary

- Builds: a real Keycloak for test and development, set up for ModelHub: a realm file, a compose file that starts one pinned Keycloak (26.8.1) with the realm imported, the wiring to start it beside the stack and the Artifactory stand-in, a guide with the settings to copy to the organisation's Keycloak, and tests that run the real sign-in path against it (also in CI)
- Touches: new `deploy/keycloak/` (realm file, compose file, `up.sh`, guide), `deploy/smoke/standins.py` (an option to run only the Artifactory stand-in), `server/e2e/tests/` (real Keycloak sign-in tests), `tests/` (realm, compose, guide and pack-exclusion checks), `.github/workflows/ci.yml` (a Keycloak job)
- Tests: about 25 pytest tests: realm file and compose checks (no Docker), pack-exclusion checks, and real-Keycloak sign-in tests (Docker and Chrome)

## Steps

- [x] Step 1. Project structure and configuration: create `deploy/keycloak/` and add `deploy/keycloak/` to the "never in the pack" checks' list of names; no change to the Catalog, import service or portal code. (NFR1)
- [x] Step 2. Verify the test runner and record the unit-scoped commands: `.venv/bin/python -m pytest tests/test_keycloak_files.py -q` and `.venv/bin/python -m pytest server/e2e/tests/test_real_keycloak.py -q`. (NFR2)
- [x] Step 3. Realm definition - Red, Green, Refactor: tests that the realm file has the realm `modelhub`, the role `modelhub-admin`, the portal client `modelhub` (confidential, code flow, S256, `openid`, redirect and logout addresses, audience mapper), the service client `modelhub-artifactory-service` (client credentials only, audience mapper), the two test users (ordinary and administrator), and that every secret and password is marked as a test value; then `deploy/keycloak/modelhub-realm.json`. (FR2.1, FR2.2, FR2.3, FR3.1, FR3.2, FR3.3, FR4.1, FR6.1, NFR5)
- [x] Step 4. Keycloak container - Red, Green, Refactor: tests that `compose.keycloak.yaml` pins `quay.io/keycloak/keycloak:26.8.1` (no `latest`), publishes only `127.0.0.1:8080`, mounts and imports the realm file, runs in development mode, has a health check on the realm's discovery address, and that `docker compose config` reads it; then `deploy/keycloak/compose.keycloak.yaml`. (FR1.1, FR1.2, FR1.3, NFR2, NFR4)
- [x] Step 5. Test stack wiring - Red, Green, Refactor: tests that `up.sh` writes the stack's secrets from the realm file's test values, sets `KEYCLOAK_ISSUER=http://keycloak:8080/realms/modelhub`, starts only the Artifactory stand-in (new option in `deploy/smoke/standins.py`) beside Keycloak, and that the guide lists every realm, role, client and token claim found in the realm file; then `up.sh`, the stand-in option and `deploy/keycloak/README.md`. (FR5.1, FR5.2)
- [x] Step 6. Kept out of the pack - Red, Green, Refactor: a test that the server pack never lists any `keycloak` file and the pack build does not copy `deploy/keycloak/`. (NFR1)
- [x] Step 7. Real sign-in verification - Red, Green, Refactor: `server/e2e/tests/test_real_keycloak.py` starts the real Keycloak from the compose file, waits for the discovery address within 120 seconds, maps the name `keycloak` to 127.0.0.1 for the test and for Chrome, adds the test portal's address to the portal client's redirect addresses through Keycloak's admin interface, then: signs in to the portal in Chrome as the ordinary user and as the administrator (administrator screens open only for the second), makes a personal token in the portal, and shows the import service's own client-credentials token accepted by the Catalog; skips with a clear message where Docker or Chrome is missing. (FR6.2, NFR3)
- [x] Step 8. Environment/build configuration: a CI job `keycloak (real sign-in)` on the runner's Docker and Chrome runs the real tests; a test checks the job is there. (FR6.3)
- [x] Step 9. Documentation and traceability: `deploy/keycloak/README.md`, a line in `deploy/README.md`, the traceability file. (FR5.2)

## Testing Contract

```json
{
  "version": 1,
  "methodology": "tdd",
  "source": "team",
  "ordering": "Write a failing test for each behaviour first, then the code that makes it pass, then tidy up.",
  "scope": "feature",
  "test_strategy": "standard",
  "project_type": "brownfield",
  "applicable_notes": [
    {
      "layer": "org",
      "text": "We treat tests as a first-class deliverable in every Bolt. The specific\nmethodology (TDD, BDD, ATDD, or classic test-after) is affirmed at\npractices-discovery and recorded in `team.md` under this heading with explicit\n`Methodology` and `Ordering` fields; Code Generation resolves those fields\nindependently from coverage, tooling, and scope notes.\n\nWhen no posture has been affirmed, our default per scope is:\n- **Methodology**: test-after\n- **Ordering**: implement each applicable testable layer, then write and run\n  that layer's tests.\n- `mvp`, `enterprise`, `feature`, `infra`, `classic` add an 80% line-coverage\n  floor and CI execution before merge.\n- `bugfix`, `security-patch` add a targeted regression for the specific\n  bug/vulnerability and require the existing suite to remain green.\n- `express` uses the Minimal strategy: requirement-driven unit tests (one per\n  requirement, with a happy-path floor per component); existing tests remain\n  green.\n- `poc`, `refactor`, `workshop` add no extra new-test floor and require the\n  existing suite to remain green.\n\nThe active `Test Strategy` still applies in every scope and determines test\nvolume/types. Scope floors are additive; they never reduce or replace the\nselected strategy.\n\nBuild and Test verifies defined coverage floors and affirmed quality targets;\nthey may not be weakened to make a step pass.\n\nAffirm a stricter posture in `team.md` if the team commits to one."
    },
    {
      "layer": "team",
      "text": "- **Methodology**: tdd\n- **Methodology evidence**: chosen in the interview (Q4); the existing prototype's tests were written after the code, so this is a change of habit for new work.\n- **Ordering**: Write a failing test for each behaviour first, then the code that makes it pass, then tidy up.\n- Every change has a test for it, and the existing tests keep passing. There is no percentage coverage floor.\n- The test tool is `pytest`; tests live in `tests/`."
    }
  ],
  "obligations": {
    "strategy": "standard",
    "strategy_volume": [
      "Five to eight tests per component.",
      "Unit tests plus integration tests for key boundaries.",
      "Add E2E, performance, or security tests when requirements demand them."
    ],
    "scope_floor": [
      "Meet an 80% line-coverage floor.",
      "Run the selected tests in CI before merge."
    ],
    "combination_rule": "Apply every selected-strategy obligation and every scope-floor obligation; neither replaces the other, and a targeted scope regression may add the narrowest necessary test type beyond the strategy default."
  },
  "plan_profile": {
    "methodology": "tdd",
    "runner_step": "Verify the existing test runner/configuration and record the exact unit-scoped command.",
    "runner_ready_before_first_test": true,
    "testable_layers": [
      "Data model / database behavior",
      "Repository / data access",
      "Business logic",
      "API / endpoint",
      "Frontend behavior"
    ],
    "steps": [
      "Project structure and production configuration skeleton.",
      "Verify the existing test runner/configuration and record the exact unit-scoped command.",
      "Data model / database behavior - Red: write the failing tests and record the failing command output.",
      "Data model / database behavior - Green: implement only enough behavior to pass.",
      "Data model / database behavior - Refactor: improve the implementation while tests stay green.",
      "Repository / data access - Red: write the failing tests and record the failing command output.",
      "Repository / data access - Green: implement only enough behavior to pass.",
      "Repository / data access - Refactor: improve the implementation while tests stay green.",
      "Business logic - Red: write the failing tests and record the failing command output.",
      "Business logic - Green: implement only enough behavior to pass.",
      "Business logic - Refactor: improve the implementation while tests stay green.",
      "API / endpoint - Red: write the failing tests and record the failing command output.",
      "API / endpoint - Green: implement only enough behavior to pass.",
      "API / endpoint - Refactor: improve the implementation while tests stay green.",
      "Frontend behavior - Red: write the failing tests and record the failing command output.",
      "Frontend behavior - Green: implement only enough behavior to pass.",
      "Frontend behavior - Refactor: improve the implementation while tests stay green.",
      "Environment/build configuration.",
      "Documentation and traceability."
    ]
  },
  "input_sha256": "sha256:6f4084396966f6e9af79e75a17cc1b9185a44274ce3ce1404a4c8abc7e69e609",
  "contract_sha256": "sha256:807be3333a2009bf0be53c232b154f2b8fef0ac157419e4bd4a2c74e53396edb"
}
```
