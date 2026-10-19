# Architecture Decisions

- **ADR-001: Four building blocks**
  - **Context** — The work adds one container and its settings; it must stay out of the signed server pack and be testable against the real thing.
  - **Decision** — Four blocks: RealmDefinition, KeycloakContainer, TestStackWiring, SignInVerification (the person's choice at Q1).
  - **Consequences** — The realm file is the single source, read by the container, the wiring and the tests; the container version can change without touching the realm; slightly more files than a single folder of scripts.
  - **Alternatives Rejected** — Two blocks (everything that defines Keycloak, and the verification): the realm file changes at a different rate than the container version and is read by three others.

- **ADR-002: Test-only, outside the server pack**
  - **Context** — The real server uses the organisation's Keycloak (an outside system); a Keycloak with fixed test secrets must never reach it. (FR5.1, NFR1)
  - **Decision** — A separate compose file under `deploy/keycloak/`, never listed in the pack; a test fails if the pack holds any of it.
  - **Consequences** — Safe by construction; the pack and its tests gain one check.
  - **Alternatives Rejected** — Putting Keycloak in the main stack file: every install would carry fixed test secrets.
