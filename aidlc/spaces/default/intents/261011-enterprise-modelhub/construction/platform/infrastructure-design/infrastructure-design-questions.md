# Infrastructure Design Questions: platform

Context: this is the hosting design for the whole system on the one Linux server with Docker: the containers, the Compose file, networks, volumes, secrets, the image path through the internal registry and the upgrade-and-return steps. The following are settled by earlier answers and written as such: production only; alerts routed by the existing central monitoring; Debian-based images scanned in the build; secrets as files under /run/secrets; PostgreSQL in a container with one schema and user per service; a 100 GB database volume and a 500 GB import working volume; recovery within 4 business hours. One choice is yours and it shapes the whole picture.

My defaults (not questions): Docker Engine with the Compose plugin (version 2); one host name for everything; the images, the Compose file and a short operator guide travel together as one signed "server pack" (signed with the same kind of signing key the bundles use, checked on the server before loading); an operator script creates the secret files (generating the random ones, asking for the external ones such as the Artifactory token) and the database users; backup of the database volume is left to the later phase in the scope, but the design keeps the data on one named volume so it can be backed up by stopping the stack and copying it.

## Q1. How should people and the CLI reach the services?

Why we ask: the portal (for people) and the import and retention routes of `artifactory-service` (for the CLI and the portal) must be reachable over TLS, while the Catalog and the database must not be reachable at all. Something has to terminate TLS and route by path.

- Option A, a small reverse proxy container in our stack (nginx from the official image) that holds the organisation's certificate as secret files, publishes only port 443, serves the portal at `/` and forwards `/v1/imports...` to `artifactory-service`. Everything else is internal. Pros: self-contained; one thing to publish; the same on every server. Cons: one more container; the certificate and its renewal are ours to place on the server.
- Option B, the organisation's existing load balancer or reverse proxy in front: our stack publishes the portal and the service on two ports bound to the server's address (no TLS inside), and the organisation's proxy terminates TLS and routes. Pros: uses the organisation's certificate handling and policies; no proxy container to maintain. Cons: depends on that team; traffic between the proxy and the server is plain unless they add TLS; a port to firewall.
- Option C, each service serves TLS itself (uvicorn with the certificate) on its own port. Pros: no proxy. Cons: certificates in three places; people need two addresses; the CLI and portal have different ports to remember.
- Recommendation: A. Option B is a reasonable alternative if your organisation requires all traffic to pass its own proxy; the rest of the design is the same either way.

A. Option A: a reverse proxy container in our stack
B. Option B: the organisation's existing proxy or load balancer in front
C. Option C: each service serves TLS itself
D. Not yet defined
X. Other (please specify)

[Answer]: A
