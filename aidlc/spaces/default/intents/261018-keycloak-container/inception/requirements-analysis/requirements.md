# Requirements: Keycloak for ModelHub

## Intent analysis

Give the team a real Keycloak, already set up for ModelHub, to start beside the server stack and test the sign-in path against, and write down the exact settings so the organisation's own Keycloak can be set up the same way. The real server keeps using the organisation's Keycloak; this setup is for test and development only, never part of the signed server pack. Artifactory is not involved: the stand-in is used. Depth: Minimal (clear request, one new container, well-understood domain).

## Functional requirements

- **FR1 The Keycloak container**
  - **FR1.1** A compose file `deploy/keycloak/compose.keycloak.yaml` starts one Keycloak container from the official image, pinned to an exact version (not `latest`).
  - **FR1.2** The container imports a realm file `deploy/keycloak/modelhub-realm.json` when it starts, so no step is done by hand in the Keycloak screens.
  - **FR1.3** It starts in a development mode that needs no certificate and no external database (hardening is out of scope), reachable by the browser and by the other containers under one fixed address.
- **FR2 The realm**
  - **FR2.1** One realm named `modelhub`; its issuer address is the value the stack's `KEYCLOAK_ISSUER` takes.
  - **FR2.2** A role `modelhub-admin` in the realm; a person who holds it appears in tokens under `realm_access.roles`.
  - **FR2.3** Every access token the stack accepts carries the audience `modelhub`, the person's `sub` and `preferred_username` (the code in the Catalog, the import service and the portal checks these).
- **FR3 The clients**
  - **FR3.1** A client with the id `modelhub` for the portal: confidential, authorisation code with a proof key (S256), scope `openid`, redirect address and logout address of the test portal, a client secret.
  - **FR3.2** A client with the id `modelhub-artifactory-service` for the import service: confidential, client credentials only, its tokens carry audience `modelhub` and `azp` equal to its id.
  - **FR3.3** The ID token of the portal client carries the audience the portal checks (its own client id).
- **FR4 The test people**
  - **FR4.1** One ordinary test user and one administrator test user (holding `modelhub-admin`), with known test passwords.
- **FR5 Use with the stack**
  - **FR5.1** A second compose file adds Keycloak beside the existing stack and the Artifactory stand-in, with the stack's settings (issuer, secrets, client ids) filled from the realm file's test values, so the whole thing starts with one command.
  - **FR5.2** A short guide (`deploy/keycloak/README.md`) says how to start it, sign in as each test user, and lists the realm, role, clients and token claims to set up in the organisation's Keycloak.
- **FR6 Tests**
  - **FR6.1** A test checks the realm file: names, clients and their flows, the role, the users, the audience mapping, and that every secret in it is marked as a test value.
  - **FR6.2** A test starts the real Keycloak from the compose file and shows the sign-in path working against it: the portal login in Chrome as the ordinary and as the administrator user, a personal token made in the portal, and the import service obtaining its own token and being accepted by the Catalog.
  - **FR6.3** The CI runs that test (it needs Docker and Chrome, both on the runner).

## Non-functional requirements

- **NFR1 Test-only and kept out of the pack** The server pack and its build never include the Keycloak files; a test fails if they do. The test secrets are marked as such and the guide says this setup is never for a real server.
- **NFR2 Reproducible** The image is pinned to an exact version; the realm file is the single source of the Keycloak settings.
- **NFR3 Start time** The Keycloak is ready (the realm's discovery address answers) within 120 seconds of starting on a CI runner.
- **NFR4 No outside connection** Starting it needs no download after the image is present, and it makes no call to the internet.
- **NFR5 Secrets** The only secrets in the repository are the marked test values; the repository's secret scanning must not flag the realm file as a real secret (values are plainly test words).

## Constraints

- Keycloak is an external system in the design; nothing in the Catalog, the import service or the portal may change except configuration values.
- Artifactory is not set up: the stand-in is used.
- Team practices: tests first, `pytest`, `ruff`, trunk-based, squash merge.

## Assumptions

- Docker is available where the tests run (it is on the CI runner and on the person's computer).
- The latest stable Keycloak 26 release is acceptable; the exact version is chosen and pinned in design after checking which images exist.

## Out of scope

Keycloak production hardening (its own database, TLS, clustering, backups), single sign-on with the organisation's directory, anything about Artifactory itself.

## Open questions

- Which exact Keycloak version to pin (settled in design).

## Assumptions & Open Questions

- The latest stable Keycloak 26 release is acceptable; the exact version is chosen in design.
- Which exact Keycloak version to pin is settled in design.
