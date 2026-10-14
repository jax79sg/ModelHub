# Infrastructure Specification: catalog

The Catalog is one container beside a PostgreSQL container on the one Linux server with Docker. The Compose file, networks, volumes and secrets for the whole server are specified in the platform unit; this document says what the Catalog and its database need from them. One production stack only (infrastructure question 1 A).

## Deployment

| Facet | Choice | Rationale |
|---|---|---|
| Compute model | Two containers under Docker Compose: catalog (Python 3.12 slim) and its PostgreSQL 16 | Decided scope: one Linux server with Docker, no orchestrator (FR6.1) |
| Networking | Both on the internal Docker network only; the Catalog is reached by the portal and the import service by service name; nothing is published on the host | NFR5.3, only the entry point is reachable from outside |
| Storage | Named volume `catalog-db` for PostgreSQL data; no volume for the Catalog (it holds no files) | NFR3.3, data survives restarts and upgrades |
| Environments | Production only on the server; developers run the same Compose file locally with the stand-in; a staging project can be added later under another project name | Infrastructure question 1 A |
| Infrastructure as code | The Compose file and the database set-up step, kept in the repository and reviewed like code | Reproducible, reviewable changes |
| Resource sizing | Catalog: memory limit 1 GB, half a core reserved; database: 4 GB memory, volume 100 GB | NFR2.1, NFR7.2, NFR7.3: 20 people at once, about 10,000 versions |
| Restart and start order | Restart on failure; the Catalog waits for the database's health check; stop grace 30 seconds | NFR4.3, NFR4.4 |
| Run-as | Non-root user, read-only root file system, only /tmp writable | NFR5.3 least privilege (platform unit sets it for all) |

## Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| PostgreSQL 16 | Database for the Catalog schema | Own database and users: runtime role (insert/select only on the trail table) and migration role; English full-text configuration; pg_trgm extension; statement timeout 5 s set by the Catalog; max 20 connections | Official Debian-based image mirrored by digest; shared container with the artifactory-service schema (separate user and schema) |
| Catalog service | FastAPI application on uvicorn | 10-connection pool; 5 s connect and 30 s read limits; listens on an internal port; reads secrets database_password and token_hash_pepper from /run/secrets | One copy |
| Keycloak (outside) | Token issuer | Only its published key address is fetched | Existing service, not in the containers |
| Central logging and monitoring (outside) | Collects standard output and polls /healthz and /readyz | No agent in our containers | Existing service |

## Shared Infrastructure

| Shared Resource | Owner Unit | Consumer Units | Access Boundary |
|---|---|---|---|
| PostgreSQL container | platform | catalog, artifactory-service | Separate schema and database user per service; the migration role is separate from the runtime role |
| Internal Docker network | platform | catalog, artifactory-service, portal | Not published on the host |
| Secrets files | platform | catalog, artifactory-service, portal | Each service mounts only its own secrets |
