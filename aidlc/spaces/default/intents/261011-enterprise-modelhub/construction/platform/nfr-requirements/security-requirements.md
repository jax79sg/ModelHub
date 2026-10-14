# Security Requirements: platform

What the packaging must guarantee about secrets, images and exposure.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR5.1 | Secrets (database password, Keycloak client secrets, Artifactory token, token-hash pepper) are mounted as files under /run/secrets and never placed in images, environment variables, project files, logs or the Compose file. | A check searches images, environment and logs for each secret (AC6.1) | NFR5b, FR6.4 |
| NFR5.2 | Containers run as a non-root user, with a read-only root file system where the service allows it, and with no extra privileges. | A check lists user, capabilities and mounts for each container | NFR5 |
| NFR5.3 | Only the entry point is reachable from outside the server; the Catalog, the database and the internal ports are on an internal network only. | A port scan from another machine finds only the entry point | NFR5a |
| NFR5.4 | All access from people and from the CLI is over TLS. | A request over plain http is refused or redirected; the certificate is the organisation's | NFR5 |
| NFR5.5 | The database user of each service reaches only its own schema. | Set up by the platform's start-up step; a check tries the reverse | NFR5, FDQ5 A |
| NFR5.6 | Images are scanned in the build; a critical finding that has a fix blocks the release. | A scanner step in the release workflow | NFR5, NFR questions Q2 A |
| NFR5.7 | Images are tagged with the release version and a content digest, never latest. | The Compose file names tags; a check refuses latest | NFR5, FR6.6 |
| NFR5.8 | The model files are served only through Artifactory; no container serves them. | No volume of model files is mounted into any container except the temporary working folder of the import service | NFR5d |
| NFR5.9 | The import service's working folder is on storage separate from the database's, so a full import disk cannot stop the database. | Two volumes | NFR5, NFR7 |
