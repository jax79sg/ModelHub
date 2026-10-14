# Infrastructure Specification: portal

One container that serves the web pages. It calls the Catalog and the retention and key part of artifactory-service by service name on the internal Docker network and signs people in with the existing Keycloak. People reach it through the entry point decided in the platform unit. One production stack only.

## Deployment

| Facet | Choice | Rationale |
|---|---|---|
| Compute model | One container (Python 3.12 slim) under Docker Compose, uvicorn with 4 workers | NFR2.1, NFR7.1: 20 people at once |
| Networking | Internal Docker network; the entry point forwards to it; outbound to the Catalog, artifactory-service and Keycloak only | NFR5.3, NFR8.1 |
| Storage | None persistent; a writable /tmp only; sessions in memory | NFR9.4: a restart signs everyone out |
| Environments | Production only on the server; developers run it locally with the stand-ins | Infrastructure question 1 A |
| Infrastructure as code | Compose file in the repository | Reviewed like code |
| Resource sizing | Memory limit 1 GB; half a core reserved | NFR2.3: small pages |
| Restart and start order | Restart on failure; waits for the Catalog's health; stop grace 20 seconds | NFR3.1 |
| Run-as | Non-root, read-only root file system | NFR5 least privilege |

## Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| Portal service | FastAPI with Jinja2 pages | 4 workers; session idle limit 8 hours; settings for Catalog and service addresses, Artifactory address and repository key (for the fetch instructions), Keycloak realm and client; reads the sign-in client secret from /run/secrets | One copy |
| Keycloak (outside) | Sign-in | Client `modelhub` with the authorisation code flow and proof key; redirect address of the portal; realm role modelhub-admin | Existing; client created by the Keycloak administrators |
| Catalog and artifactory-service | Data and retention | Called with the person's token and request id; 5 s connect and 30 s read limits | Internal |
| Central logging and monitoring (outside) | Collects standard output; polls health | No agent in our container | Existing |

## Shared Infrastructure

| Shared Resource | Owner Unit | Consumer Units | Access Boundary |
|---|---|---|---|
| Entry point | platform | portal, artifactory-service | TLS; routes by path |
| Internal Docker network | platform | portal, catalog, artifactory-service | Not published on the host |
