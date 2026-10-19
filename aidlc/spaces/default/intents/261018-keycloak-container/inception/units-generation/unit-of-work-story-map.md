# Unit Story Map

| ID | Implementing Unit | Directory |
|---|---|---|
| FR1 | U1 | u1-keycloak |
| FR1.1 | U1 | u1-keycloak |
| FR1.2 | U1 | u1-keycloak |
| FR1.3 | U1 | u1-keycloak |
| FR2 | U1 | u1-keycloak |
| FR2.1 | U1 | u1-keycloak |
| FR2.2 | U1 | u1-keycloak |
| FR2.3 | U1 | u1-keycloak |
| FR3 | U1 | u1-keycloak |
| FR3.1 | U1 | u1-keycloak |
| FR3.2 | U1 | u1-keycloak |
| FR3.3 | U1 | u1-keycloak |
| FR4 | U1 | u1-keycloak |
| FR4.1 | U1 | u1-keycloak |
| FR5 | U1 | u1-keycloak |
| FR5.1 | U1 | u1-keycloak |
| FR5.2 | U1 | u1-keycloak |
| FR6 | U1 | u1-keycloak |
| FR6.1 | U1 | u1-keycloak |
| FR6.2 | U1 | u1-keycloak |
| FR6.3 | U1 | u1-keycloak |

## Cross-cutting

None: every requirement belongs to the one unit.

## Implementation order within U1

1. The realm file and its check (FR2 to FR4, FR6.1).
2. The Keycloak container compose file (FR1).
3. The test stack wiring and guide (FR5).
4. The real sign-in tests and the CI job (FR6.2, FR6.3).

## Coverage verification

All 21 enumerated FR ids are assigned to U1, and U1 has rows.
