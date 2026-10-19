# Build and Test Summary

## Overall status

Build: success (`ruff check .`, `ruff format --check .` clean, compose files read). Tests: 1187 passed, 0 failed locally. Targets: **7 Met, 0 Unverified, 0 Not Met** of 7. The CI job `keycloak (real sign-in)` ran the 8 real tests on the runner's Chrome 155 and passed (PR 30).

## Test type inventory

Unit and file checks (`tests/test_keycloak_files.py`, 25 tests: realm, container, wiring, guide, pack, CI, the stand-in option run for real), and integration tests against the real Keycloak (`server/e2e/tests/test_real_keycloak.py`, 8 tests). Performance and security instruction files are not generated at the Standard strategy; the one timing target (ready within 120 s) and the secret-marking target are checked by tests.

## Coverage expectations per unit

Standard strategy: five to eight tests per component. RealmDefinition 8, KeycloakContainer 7, TestStackWiring 9, SignInVerification 8 plus the CI check. Counts of the rest of the project: CLI 515, web 24, common 99, catalog 154, import service 183, stand-in 95, portal 92, test helpers 15, e2e 10 (of which 8 are the real Keycloak tests).

## Readiness assessment

- Build-ready: yes.
- Test-ready: yes; all tests pass and CI passed the Keycloak job.
- Deployment-ready: not a deployment: this unit is a test and development aid, never part of the signed pack. It is ready to use for testing the sign-in; setting up the organisation's Keycloak is still done by its owners using the guide in `deploy/keycloak/README.md`.

## Known limitations or outstanding items

- Only Keycloak 26.8.1 is tried. Production hardening, directory single sign-on and Artifactory itself are out of scope by the person's choice.
- The real tests need Docker, Chrome and Playwright; they skip without them (CI fails a skipped run).
- The readings used: the scope's 80% line floor is read as every executable line of the one new Python source file being run by a test (21 of 21); no coverage tool is configured.

## Target Verification Matrix

| Target ID | Source | Expected | Actual | Evidence | Owning Stage | Verdict |
|---|---|---|---|---|---|---|
| NFR1 | requirements.md NFR1 | The pack and its build never include the Keycloak files; test secrets marked | Holds | `tests/test_build_pack.py` (no `keycloak` in the pack list), `tests/test_keycloak_files.py` (build script, marked secrets) | build-and-test | Met |
| NFR2 | requirements.md NFR2 | Image pinned exactly; the realm file the single source | Holds | `tests/test_keycloak_files.py` (`quay.io/keycloak/keycloak:26.8.1`, never latest) | build-and-test | Met |
| NFR3 | requirements.md NFR3 | Ready within 120 seconds on a CI runner | Holds | `test_keycloak_is_ready_within_two_minutes`: 32 s locally; CI job passed (PR 30) | build-and-test | Met |
| NFR4 | requirements.md NFR4 | No call to the internet | Holds | `test_keycloak_starts_and_serves_its_realm_on_a_network_with_no_route_out` (healthy on a network with no route; 1.1.1.1 unreachable); CI passed | build-and-test | Met |
| NFR5 | requirements.md NFR5 | Only marked test secrets; secret scanning not tripped | Holds | `test_every_secret_and_password_is_plainly_marked_as_a_test_value`; the PR's GitGuardian check is the scanner (see test-results.md) | build-and-test | Met |
| Testing Contract | `code-generation-plan.md` (tdd, standard) | Tests first; 5 to 8 per component | Holds | 8, 7, 9, 8 tests per component; the real tests found a realm field Keycloak rejects | build-and-test | Met |
| Testing Contract floor | `code-generation-plan.md` (80% line floor, CI before merge) | New Python source covered; selected tests run in CI | Holds | 21 of 21 executable lines of `standins.py` run (`trace`); CI job `keycloak (real sign-in)` passed | build-and-test | Met |
