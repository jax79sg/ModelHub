# Infrastructure Specification: artifactory-service

One container that receives bundles, re-checks them, uploads to the existing Artifactory with the JFrog CLI, records through the Catalog and runs retention. It uses the same PostgreSQL container as the Catalog (its own schema and user) and a separate working volume for received pieces. One production stack only.

## Deployment

| Facet | Choice | Rationale |
|---|---|---|
| Compute model | One container (Python 3.12 slim plus the JFrog CLI binary and a pinned huggingface_hub) under Docker Compose | Only this unit carries these tools (unit boundary) |
| Networking | Internal Docker network; outbound to Artifactory (its address as a setting), to the Catalog by service name, to PostgreSQL and to Keycloak's key address; reached by the CLI through the entry point (path /v1/imports only) and by the portal directly on the internal network | NFR5.3, NFR8.1 |
| Storage | Named volume `import-work` of 500 GB for pieces and unpacked files, separate from the database volume; its own schema in the database volume `catalog-db` | NFR7.6, NFR5.9 of the platform unit |
| Environments | Production only on the server; developers run it with the Artifactory stand-in and a local PostgreSQL | Infrastructure question 1 A (asked at the Catalog) |
| Infrastructure as code | Compose file and database set-up step in the repository | Reviewed like code |
| Resource sizing | Memory limit 2 GB (blocks of 8 MiB keep peak memory low); one core reserved; disk work needs about 100 MB/s | NFR7.1, NFR7.2, NFR7.3 |
| Restart and start order | Restart on failure; waits for the database health; stop grace 60 seconds; at start-up interrupted imports are failed and working files swept | NFR4.2, NFR4.3 |
| Run-as | Non-root user, read-only root file system except the import-work volume and /tmp, no extra capabilities | NFR5.5 |

## Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| artifactory-service | FastAPI application on uvicorn plus the import runner | Max 2 running imports; piece blocks of 8 MiB; idle cancel after 24 hours; reads secrets database_password, keycloak_client_secret and artifactory_token | One copy |
| JFrog CLI (jf) | Runs `jf hf upload` | Pinned release; update checks and telemetry off; configured at run time from a private temporary file made from the secret | Inside the service image |
| PostgreSQL 16 (shared container) | Database for this service's schema | Own schema and user that cannot reach the Catalog's tables; numbered migrations under a lock | Same container as the Catalog |
| Artifactory (outside) | Holds the models | Hugging Face repository with the Machine Learning layout; service account with deploy and delete rights on that repository only | Existing; its version must be 7.77.1 or later |
| Keycloak (outside) | Token issuer | Client modelhub-artifactory-service with client credentials | Existing |
| Central logging and monitoring (outside) | Collects standard output and polls /healthz and /readyz | No agent in our containers | Existing |

## Shared Infrastructure

| Shared Resource | Owner Unit | Consumer Units | Access Boundary |
|---|---|---|---|
| PostgreSQL container | platform | catalog, artifactory-service | Separate schema and user per service |
| Entry point | platform | artifactory-service (for the CLI) | TLS; only the import route (/v1/imports) of this service is exposed through the proxy |
| Artifactory service account | Artifactory administrators | artifactory-service | Deploy and delete on the one repository only; its token is a secret file |
