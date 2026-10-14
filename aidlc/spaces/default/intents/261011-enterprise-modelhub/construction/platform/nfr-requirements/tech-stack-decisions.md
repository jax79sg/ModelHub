# Technology Decisions: platform

Choices for the packaging. The server stack is Python 3.12 (decided once for all server units).

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR9.1 | Docker Engine with Docker Compose on one Linux server that already has Docker; no orchestrator. | Compose file with named services, networks, volumes and secrets | FR6.1, FQ1, FQ8 A |
| NFR9.2 | Images: python:3.12-slim for the three services; postgres:16 for the database (official Debian-based images). | Mirrored to the internal registry by digest | NFR9, NFR questions Q1 A |
| NFR8.1 | Images are built on the internet side and reach the server through the internal container registry; nothing is downloaded while running. | The running containers have no route to the internet | NFR8, FR6.2 |
| NFR6.1 | Every container writes logs to standard output as JSON lines and has a health check using the live and ready paths. | Docker health checks; the central logging collects the output | NFR6, FR6.5 |
| NFR3.1 | Every container has a restart policy (restart on failure); the database starts first and the others wait for its health. | Compose dependencies on health | NFR3 |
| NFR3.2 | Back within 4 business hours: the previous image tags stay in the registry and on the server. | The documented return step is rehearsed once | NFR3, FR6.6 |
| NFR4.1 | An upgrade is: stop, replace images with newer tags, start; database steps run at start under a lock and keep data. | AC6.2: upgrade then return keeps the models and trail rows | NFR4, NFR6, FR6.6 |
| NFR7.1 | The database data lives on a named volume that survives restarts and image upgrades. | A test restarts and upgrades and finds the data | NFR7, FR6.3 |
| NFR7.2 | Disk planning: database volume 100 GB; the import service's working volume 500 GB. | Documented minimums checked at start by the service (rule BR1.20 of artifactory-service) | NFR7, NFR questions (artifactory-service) Q1 A |
| NFR9.3 | Build and release by the existing GitHub Actions workflow with a new job for images and an image scan; ruff and pytest checks as today. | No new CI product | NFR9, team.md |
| NFR10.1 | Not a CLI concern: the program is packaged by the existing release; this unit packages only the server side. | None | NFR10 |
