# Unit of Work

## Units

| Unit ID | Directory | Name | Kind | Size | Deployment model |
|---|---|---|---|---|---|
| U1 | u1-keycloak | keycloak | packaging | M | Standalone, test-only (never in the signed server pack) |

## U1 keycloak

- **Description:** The realm file, the Keycloak container compose file, the test stack wiring with its guide, and the tests that start the real Keycloak and run the sign-in path.
- **Boundaries:** `deploy/keycloak/` (realm file, compose files, guide), the checks of the realm file, the real sign-in tests (`server/e2e/`), and the CI job. No change to the Catalog, import service or portal code, only configuration values.
- **Responsibilities:** RealmDefinition, KeycloakContainer, TestStackWiring, SignInVerification (from `components.md`).
- **Implementation notes and constraints:** Pinned Keycloak image (exact version chosen after checking available tags); development mode, no certificate, no external database; fixed marked test secrets; the pack and its tests must not include any of it; tests first, pytest, ruff.
