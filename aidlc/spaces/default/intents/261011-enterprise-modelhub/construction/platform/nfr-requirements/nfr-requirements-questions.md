# NFR Requirements Questions: platform

Context: "NFR" means quality targets. `platform` is the packaging: the container images, the Compose file, secrets, health checks, logging, the image path through the internal registry and the upgrade-and-return steps. As a packaging unit it owes only security and technology decisions. Already settled and reused: the stack (Python 3.12), recovery within 4 business hours, up to 20 people at once, no connection to the internet while running (NFR8), data that survives restarts and image upgrades (FR6.3), an upgrade that stops, replaces images and starts again with the previous tags kept (FR6.6).

My defaults for this unit (not questions): containers run as a non-root user with a read-only root file system where possible; secrets are mounted from files under /run/secrets; only the portal's port is published on the server (the Catalog, the import service and the database are on an internal Docker network, except the import service's address which the CLI needs, behind the same entry point); every container has a restart policy and a health check; images are tagged with the release version, never "latest".

## Q1. Which base images should the containers use?

Why we ask: the images are built on the internet side and carried through the internal registry, and the server team may have a preferred operating-system family.

- Option A, the official Debian-based images (`python:3.12-slim` for our services, `postgres:16` for the database). Pros: widely used; well documented; small. Cons: not the Red Hat family.
- Option B, Red Hat UBI-based images (UBI Python 3.12 for our services, a UBI-based PostgreSQL). Pros: matches a Red Hat-based organisation and its support rules. Cons: larger; the PostgreSQL image is less common; the JFrog CLI and other tools need extra installation steps.
- Recommendation: A, unless the organisation requires Red Hat images. The earlier question about RHEL 8 concerned the command-line program's compatibility, not the server images.

A. Option A: official Debian-based images
B. Option B: Red Hat UBI-based images
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. Should the images be scanned for known weaknesses before they are pushed?

Why we ask: images carry operating-system packages, which can have known weaknesses. The online side already runs scanning for the project's code (CodeQL, secret scanning, Dependabot).

- Option A, yes: an image scan runs in the build, and a critical finding that has a fix blocks the release. Pros: known issues are caught before the images cross into the organisation. Cons: needs a scanner in the build (a free one is enough) and occasional rebuilds.
- Option B, no scan; rely on rebuilding regularly. Pros: nothing to add. Cons: weaknesses go unseen.
- Recommendation: A.

A. Option A: scan in the build; block on fixable critical findings
B. Option B: no scan
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A
