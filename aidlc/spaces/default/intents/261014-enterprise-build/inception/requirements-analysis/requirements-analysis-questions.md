# Requirements Analysis Questions: enterprise build

Context: this build turns the approved design (`aidlc/spaces/default/intents/261011-enterprise-modelhub/`, start with `architecture-overview.md`) into code. The requirements are those already approved there (FR1 to FR8, NFR1 to NFR10, acceptance criteria and constraints); they are not rewritten. The questions below are the build choices the design left open.

## Q1. How should the code of the server units be laid out in the repository?

Why we ask: it fixes folders, packaging and how the images are built. The existing CLI lives in `src/modelhub` and the prototype web app in `web/`.

- Option A, a new top-level `server/` folder with one package per unit (`server/common`, `server/catalog`, `server/artifactory_service`, `server/stand_in`), each with its own project file and tests; the portal grows from `web/` in place; the CLI stays in `src/modelhub`. Pros: matches the unit boundaries; each image installs only what it needs; easy to review one unit per pull request. Cons: several project files.
- Option B, one package `modelhub_server` with a sub-package per unit and one project file. Pros: simplest packaging. Cons: every image carries every unit's code; boundaries are easier to blur.
- Recommendation: A.

A. Option A: `server/` with one package per unit
B. Option B: one package with sub-packages
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. How should tests that need PostgreSQL get one?

Why we ask: the Catalog and `artifactory-service` use real SQL (full-text search, trigram indexes, advisory locks, role permissions); a substitute database would not prove them. Docker (OrbStack) is available on this machine and GitHub Actions can start a service container.

- Option A, tests start a throwaway PostgreSQL 16 container through the Docker command line (a pytest fixture; skipped with a clear message when Docker is missing), and CI uses a PostgreSQL service container. Pros: the real thing, the same version as production; no install. Cons: needs Docker locally.
- Option B, a PostgreSQL binary installed on the machine and started by a test plugin. Pros: no Docker. Cons: a local install to maintain; version drift.
- Option C, SQLite in tests. Pros: nothing to start. Cons: cannot test the PostgreSQL features the design depends on.
- Recommendation: A.

A. Option A: throwaway PostgreSQL 16 container (Docker locally, service container in CI)
B. Option B: a local PostgreSQL binary
C. Option C: SQLite
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. How should tests get Keycloak tokens?

Why we ask: the token check, the portal sign-in and the CLI sign-in all need tokens, and a real Keycloak is not available for tests.

- Option A, a small fake token issuer in the shared test helpers: it makes an RSA key, signs tokens with chosen claims (valid, expired, wrong audience, admin, service) and serves the key-set document. A real Keycloak container is used only in the final whole-stack smoke test. Pros: fast, exact control of every failure case. Cons: the real Keycloak's quirks are seen only at the end.
- Option B, a real Keycloak container in every test run. Pros: realistic. Cons: slow, heavy, hard to make failure cases.
- Recommendation: A.

A. Option A: a fake issuer in test helpers, real Keycloak only in the smoke test
B. Option B: real Keycloak container in tests
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. What is the first thin slice (the walking skeleton)?

Why we ask: it decides what is built first and what waits for later pull requests.

- Option A, the thinnest path through every part: `common` (token check, secrets, logging, health), the stand-in (upload, list, 409), the Catalog (store a version and its trail row, models list), `artifactory-service` (create, pieces, start, full import only), the portal (sign-in and the models list), and the CLI (`login` and `import` of one bundle). Pros: proves the architecture end to end early; later work widens each part. Cons: several parts are incomplete after the first pass.
- Option B, the same but without the portal until later. Pros: smaller first pass. Cons: the portal is the person-visible end of the path.
- Recommendation: A.

A. Option A: the full thin path including the portal
B. Option B: the thin path without the portal
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A
