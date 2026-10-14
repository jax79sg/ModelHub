# Security Design: platform

How the packaging keeps secrets out of images and logs, limits what each container can do, and exposes only what must be reachable.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR5.1 | Compose secrets from files | Secrets are declared in the Compose file as file-backed secrets and appear inside each container only as files under /run/secrets, readable by that service's user; no secret value is an environment variable, a build argument or part of an image layer. |
| NFR5.2 | Least privilege per container | Each service runs as its own non-root user with a read-only root file system (writable only on its working volume and a temporary folder), all extra capabilities dropped, and no new privileges. |
| NFR5.3, NFR5.4 | Single entry point with TLS | Only the entry point is published on the server; all other services sit on an internal Docker network. The entry point terminates TLS with the organisation's certificate and refuses plain http. Its exact form is decided in Infrastructure Design. |
| NFR5.5 | Database set-up step | A one-time step run by the platform creates one schema and one user per service with rights on that schema only, and a separate migration role. |
| NFR5.6 | Image scan in the release workflow | A scan step in the existing GitHub Actions release workflow fails the release on a critical finding that has a fix. |
| NFR5.7 | Pinned tags and digests | The Compose file names each image by release version and digest; a check refuses latest. |
| NFR5.8 | No model files in containers | No volume of model files is mounted anywhere; only the import service's temporary working folder holds model data, and only while an import runs. |
| NFR5.9 | Separate volumes | The database volume and the import working volume are separate, so a full working disk cannot stop the database. |
| NFR3.1, NFR3.2 | Restart policy and kept images | Restart on failure; the database starts first and the others wait for its health; the previous image tags stay in the registry and on the server for the return step. |
| NFR4.1, NFR7.1 | Upgrade and data volume | An upgrade stops the services, replaces the image tags and starts them; database steps run at start under a lock; the database data directory is a named volume that survives all of this. |
| NFR6.1 | Health checks and standard output logging | Each container has a Docker health check on its live and ready paths and writes JSON lines to standard output for the central logging. |
| NFR7.2 | Disk plan | Database volume 100 GB; import working volume 500 GB; both documented as minimums. |
| NFR8.1, NFR9.1, NFR9.2, NFR9.3 | Compose on one server, images through the registry | Docker Engine with Compose; official Debian-based images mirrored by digest to the internal registry; no route to the internet from the running containers; built and scanned by the existing GitHub Actions workflow with a new image job. |
| NFR10.1 | Not a program concern | The command-line program is packaged by the existing release; this unit packages the server side only. |
