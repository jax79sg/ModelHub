# Requirements: enterprise ModelHub build

## Purpose

Build the enterprise ModelHub described in the approved design `aidlc/spaces/default/intents/261011-enterprise-modelhub/` (read `architecture-overview.md` first). The functional and quality requirements are those already approved there and are not copied or changed here; this document says what is built in this piece of work and how it is accepted. [desc]

## Requirements Carried From The Approved Design

| Group | Where it is written | Built by unit |
|-------|---------------------|---------------|
| FR1 Importing a model (FR1.1 to FR1.14) | `inception/requirements-analysis/requirements.md` of 261011 | import-cli, artifactory-service |
| FR2 Recording the information (FR2.1 to FR2.8) | same | catalog |
| FR3 The portal (FR3.1 to FR3.8) | same | portal, catalog |
| FR4 Access and personal tokens (FR4.1 to FR4.6) | same | catalog, artifactory-service, portal, common |
| FR5 Retention (FR5.1 to FR5.7) | same | artifactory-service, catalog, portal |
| FR6 Hosting (FR6.1 to FR6.6) | same | platform, common |
| FR7 The Artifactory stand-in (FR7.1 to FR7.3) | same | artifactory-stand-in |
| FR8 Importing the old folder store | same | reserved option only (deferred, FR8) |
| NFR1 to NFR10 and the per-unit targets | `construction/<unit>/nfr-requirements/` of 261011 | all |
| Entities, rules (BR), workflows | `construction/<unit>/functional-design/` of 261011 | all |
| Contracts C1 to C8 | `inception/contract-design/contract-summary.md` of 261011 | all |

## Build Requirements (new in this piece of work)

- **BQ1.** The code is laid out as a new top-level `server/` folder with one package per unit (`server/common`, `server/catalog`, `server/artifactory_service`, `server/stand_in`), each with its own project file and tests; the portal grows from `web/` in place; the CLI additions stay in `src/modelhub`. [Q1 A]
- **BQ2.** Tests that need PostgreSQL start a throwaway PostgreSQL 16 container through the Docker command line (a pytest fixture that skips with a clear message when Docker is missing); CI uses a PostgreSQL service container. [Q2 A]
- **BQ3.** Tests get Keycloak tokens from a fake issuer in the shared test helpers (RSA key, signed tokens with chosen claims, a key-set document). A real Keycloak container is used only in the final whole-stack smoke test. [Q3 A]
- **BQ4.** The first slice (walking skeleton) is the thinnest path through every part: `common` (token check, secrets, logging, health), the stand-in (upload, list, 409), the Catalog (store a version and its trail row, models list), `artifactory-service` (create, pieces, start, full import only), the portal (sign-in and the models list), and the CLI (`login` and `import` of one bundle). Later pull requests widen each part to the full design. [Q4 A]
- **BQ5.** Tests are written before the code (team practice) with pytest; `ruff` checks and formats with line length 100; every pull request keeps the existing 369 CLI tests and 24 portal tests passing. [team.md]
- **BQ6.** One pull request per unit (or per slice of a unit), squash-merged to `main` after all checks pass; nothing is pushed or merged without the person's say-so. [team.md, standing instruction]
- **BQ7.** No sub-agents are used, and reviews are off. [standing instruction]
- **BQ8.** No code or file contains a real secret; tests use generated test values only. [phase rules]

## Acceptance (done means)

1. Each unit's tests pass locally and in CI on the systems named in its quality targets.
2. The whole-stack smoke test (Compose with the stand-ins for Artifactory and Keycloak) imports a small bundle through the proxy with `modelhub import` and the model appears in the portal list.
3. Every functional requirement carried above has at least one automated test that names it (traceable by ID), or is recorded as deferred with the reason.
4. The upgrade-and-return rehearsal (AC6.2) passes once before first use.

## Out Of Scope For This Build

- A real Artifactory, Keycloak, registry or central logging: only their stand-ins are built; the checklist of assumptions is kept for confirmation on the real systems.
- Importing the old model-store folder (FR8): reserved, not built.
- Backup, a staging stack and any second copy of the system.

## Open Questions

- The real Artifactory's Machine Learning layout and its listing and delete calls (design item X1).
- Keycloak client and role creation (design item X3).
- Whether the organisation's certificate is trusted by import computers.

## Appendix: Requirement IDs Carried And The Unit That Builds Each

Every functional requirement ID of the approved design, with the unit that builds it (from the approved `unit-of-work-story-map.md`). FR8 and FR8.1 are deferred (a reserved option only).

| ID | Unit |
|----|------|
| FR1 | u6-import-cli |
| FR1.1 | u4-artifactory-service |
| FR1.2 | u6-import-cli |
| FR1.3 | u4-artifactory-service |
| FR1.4 | u4-artifactory-service |
| FR1.5 | u4-artifactory-service |
| FR1.6 | u4-artifactory-service |
| FR1.7 | u4-artifactory-service |
| FR1.8 | u4-artifactory-service |
| FR1.9 | u6-import-cli |
| FR1.10 | u6-import-cli |
| FR1.11 | u6-import-cli |
| FR1.12 | u4-artifactory-service |
| FR1.13 | u6-import-cli |
| FR1.14 | u4-artifactory-service |
| FR2 | u2-catalog |
| FR2.1 | u2-catalog |
| FR2.2 | u2-catalog |
| FR2.3 | u2-catalog |
| FR2.4 | u2-catalog |
| FR2.5 | u2-catalog |
| FR2.6 | u2-catalog |
| FR2.7 | u2-catalog |
| FR2.8 | u2-catalog |
| FR3 | u5-portal |
| FR3.1 | u5-portal |
| FR3.2 | u5-portal |
| FR3.3 | u5-portal |
| FR3.4 | u2-catalog |
| FR3.5 | u2-catalog |
| FR3.6 | u5-portal |
| FR3.7 | u5-portal |
| FR3.8 | u5-portal |
| FR4 | u4-artifactory-service |
| FR4.1 | u5-portal |
| FR4.2 | u4-artifactory-service |
| FR4.3 | u4-artifactory-service |
| FR4.4 | u2-catalog |
| FR4.5 | u2-catalog |
| FR4.6 | u5-portal |
| FR5 | u4-artifactory-service |
| FR5.1 | u4-artifactory-service |
| FR5.2 | u4-artifactory-service |
| FR5.3 | u4-artifactory-service |
| FR5.4 | u4-artifactory-service |
| FR5.5 | u4-artifactory-service |
| FR5.6 | u4-artifactory-service |
| FR5.7 | u4-artifactory-service |
| FR6 | u7-platform |
| FR6.1 | u7-platform |
| FR6.2 | u7-platform |
| FR6.3 | u7-platform |
| FR6.4 | u7-platform |
| FR6.5 | u1-common |
| FR6.6 | u7-platform |
| FR7 | u3-artifactory-stand-in |
| FR7.1 | u3-artifactory-stand-in |
| FR7.2 | u3-artifactory-stand-in |
| FR7.3 | u3-artifactory-stand-in |
| FR8 | u6-import-cli |
| FR8.1 | u6-import-cli |

## Sources

- [desc] Initial description: "Build the enterprise ModelHub from the approved design ... Walking skeleton first ... Tests first (pytest), ruff line length 100, one pull request per unit, run inline with no sub-agents."
- [Q1] to [Q4] The answers in `requirements-analysis-questions.md`.
- The approved design under `aidlc/spaces/default/intents/261011-enterprise-modelhub/`.
