# Technology Decisions: artifactory-service

Choices for this unit. The shared stack (Python 3.12, FastAPI, uvicorn, psycopg 3 with plain SQL) applies.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR10.1 | A Linux container with Python 3.12 and the JFrog CLI; the CLI's own platforms are decided in import-cli. | Image built on the internet side and moved through the internal registry | NFR8, NFR10 |
| NFR9.1 | Python 3.12, FastAPI, uvicorn, psycopg 3 with plain SQL and numbered migrations, in its own schema of the same PostgreSQL. | Shared stack; own database user | NFR9, NFR questions Q1 A |
| NFR9.2 | The JFrog CLI (jf) runs `jf hf upload` as a separate process; huggingface_hub is pinned to a release Artifactory supports (up to 1.19.0; large-file transfer layer up to 1.18.0). | Versions pinned in the image; verified when a real Artifactory exists | FR1.1, C5 |
| NFR9.3 | The existing bundle-checking and signing code of the CLI is reused for the second check, so both sides use one definition. | Shared as a library, not copied | FR1.14, ADR-005 |
| NFR9.4 | Tests are pytest, written before the code, run against the Artifactory stand-in and a real PostgreSQL; ruff (line length 100). | The stand-in's failure switches drive the restart tests | NFR9, team.md |
| NFR8.1 | The service connects only to Artifactory, the Catalog, PostgreSQL and (through the shared library) Keycloak. | None to the internet; the JFrog CLI's update and telemetry checks are switched off | NFR8 |
