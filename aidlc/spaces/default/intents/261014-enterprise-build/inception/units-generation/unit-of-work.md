# Units Of Work

> Carried unchanged from the approved design (`aidlc/spaces/default/intents/261011-enterprise-modelhub/inception/units-generation/unit-of-work.md`); the build uses the same seven units and the same dependency order.


Inputs: `components.md` and `decisions.md` (from `inception/domain-design/`), `requirements.md` (from `inception/requirements-analysis/`), and your answers in `units-generation-questions.md` (written UQ). The decomposition plan was approved at the plan step: one unit per deployable part, plus hosting, the stand-in and a shared library (UQ1 A, UQ2 A, UQ3 A, UQ4 A).

Unit IDs are labels. They do not say what is built first; that is chosen in Delivery Planning.

## Units

| Unit ID | Directory | Unit | Kind | Size | Deployment model |
|---------|-----------|------|------|------|------------------|
| U1 | u1-common | common | library | S | Embedded: built into the images of the server-side units |
| U2 | u2-catalog | catalog | service | L | Standalone container |
| U3 | u3-artifactory-stand-in | artifactory-stand-in | service | M | Standalone, for building and testing only; not delivered |
| U4 | u4-artifactory-service | artifactory-service | service | XL | Standalone container |
| U5 | u5-portal | portal | ui | L | Standalone container |
| U6 | u6-import-cli | import-cli | service | M | Not a container: the single-file program or offline pack, run on import computers |
| U7 | u7-platform | platform | packaging | M | Shared: the Compose file, images and secrets for the whole server |

## U1: common (library)

- **Description.** The code every server-side unit needs and that must not be copied: checking a Keycloak token and role, loading secrets and configuration from files, structured logging to standard output, and a health-check helper. [UQ2 A, FR3.1, FR6.4, FR6.5]
- **Components.** None of the nine building blocks. It is shared code that several of them use.
- **Responsibilities.** Validate a Keycloak token and report the person and whether they are an administrator; read secrets from the server's secret files and never log them; write structured logs; offer a health endpoint helper.
- **Boundaries.** No business rules and no data of its own. It makes no call to Artifactory or the database.
- **Implementation notes.** Written and tested once. Security-sensitive: tested against expired, tampered and wrong-audience tokens. Pinned to one Keycloak token format.
- **Size reasoning.** S: small, well understood, and few moving parts.

## U2: catalog (service)

- **Description.** The data interface and everything it stores about models. [DQ2 A, DQ3 A, ADR-002]
- **Components.** Catalog.
- **Responsibilities.** Own the model information, the stored documents (README, pictures, saved Hugging Face responses, manifests, bundle description files) and the import trail; store a version and its trail row in one transaction; answer the models list with filters, sort, paging and text search; mark a version removed; check every caller's token and role; make, list, revoke and check personal tokens for the CLI (stored as hashes only); own its database tables and their upgrades. [FR2, FR3.2, FR3.4, FR3.5, FR3.8, FR4.4, FR4.5, NFR2; personal tokens added by ADR-010]
- **Boundaries.** The only unit that reads or writes model information, the import trail and the personal tokens. It never calls Artifactory.
- **Implementation notes.** The models list must answer in under 1 second at 1,000 models, so the list must not read the stored documents. Documents can be large (pictures up to 7 MB). The saved responses are kept as received so unknown fields survive.
- **Size reasoning.** L: a full data model, search and filtering, and strict transactions.

## U3: artifactory-stand-in (service, test only)

- **Description.** An imitation of Artifactory's Hugging Face repository and the other calls the system makes, so the rest can be built and tested with no real Artifactory. [FR7, IQ17, IQ22 B, IQ24 A]
- **Components.** ArtifactoryStandIn.
- **Responsibilities.** Answer the calls `jf hf upload`, `snapshot_download`, listing a repository, reading checksums and deleting a version make, following JFrog's documented behaviour; record every behaviour it assumes; keep the checklist of those to confirm on a real Artifactory.
- **Boundaries.** Never delivered, and nothing in the delivered system depends on it. Used by tests of U4 (and any end-to-end check of U6 and U5).
- **Implementation notes.** Its fidelity is only as good as JFrog's documentation (risks R2, R3), so its list of assumptions is part of its deliverable.
- **Size reasoning.** M: a handful of call types (about five for upload) plus the rules, but no business logic.

## U4: artifactory-service (service)

- **Description.** Everything that touches Artifactory, in one container: the import and retention. [DQ1 B, DQ4 A, DQ5 A, DQ6 B, UQ3 A]
- **Components.** ImportService, ArtifactoryGateway, Retention.
- **Responsibilities.** Receive a verified package from the CLI; check the person's token; check the bundle's signature against its own trusted-key list and every file against the signed manifest; check names against Artifactory's rules; hold a per-model lock and an import job; decide skip, repair or full import; upload with `jf hf upload`; record through the Catalog; own the trusted-key list; hold the retention setting and decisions, list versions past the period, and carry out an administrator's keep or remove; delete from Artifactory then ask the Catalog to mark the version removed. [FR1.1, FR1.3 to FR1.8, FR1.12, FR1.14, FR4.2, FR4.3, FR5, NFR4]
- **Boundaries.** Reaches model information only through the Catalog. The only unit that holds the Artifactory credentials and the only one that carries the JFrog CLI, Python 3 and the older `huggingface_hub`.
- **Implementation notes.** The older library is pinned to a version Artifactory supports (up to 1.19.0; Xet up to 1.18.0). A stopped import must be safe to repeat. Very large packages (over 100 GB) must be received piece by piece without being held in memory, and each piece removed once unpacked (contract C1).
- **Size reasoning.** XL: the import rules, the job and lock, key management, retention and the Artifactory gateway, all with failure paths.

## U5: portal (ui)

- **Description.** The web app people use, grown from the prototype. [SQ7 A]
- **Components.** Portal.
- **Responsibilities.** Require a Keycloak sign-in; read everything through the Catalog; keep the prototype's features; add filter and sort by import time and importer, text search and the import-trail view; show how to fetch each model from Artifactory with standard tools; render model cards safely; show the retention screens to administrators only; offer a page where a person makes, sees and revokes personal tokens for the CLI; say plainly when the Catalog or Keycloak cannot be reached. [FR3, FR4.1, FR4.4 to FR4.6 (token page), FR5.3 to FR5.7 (screens), NFR5]
- **Boundaries.** Never reads the database or a folder, and never serves model files.
- **Implementation notes.** Starts from the existing web app's code, replacing the folder reading with calls to the Catalog. Keeps the existing safe-rendering protections.
- **Size reasoning.** L: many pages, though the existing app supplies most of them.

## U6: import-cli (service)

- **Description.** The changes to the existing CLI for importing. [FR1, FR8, DQ1 B]
- **Components.** SignIn, PackageSource, ImportClient.
- **Responsibilities.** Keep the person's personal token (made in the portal) in a file only they can read and present it to the import service; verify a bundle (or read an old model-store folder) with the existing code; send each verified package to the import service; show progress, retry network errors, print the report and set the exit status; never print a token. [FR1.2, FR1.9 to FR1.11, FR1.13, FR8.1]
- **Boundaries.** Needs nothing installed beyond the single-file program or its offline pack. Does not talk to Artifactory or the database. The existing `pull`, `bundle`, `verify`, `unpack`, `list` and `key` commands keep working.
- **Implementation notes.** Keeps the existing exit statuses and retry waits. Both earlier design questions are answered in Contract Design: a package is sent as the bundle's pieces, one request each, and the person signs in with a personal token.
- **Size reasoning.** M: much is reuse; the new parts are sign-in, sending and the report.

## U7: platform (packaging)

- **Description.** What makes the parts run together on the one Linux server. [FR6, FQ1, FQ8 A]
- **Components.** None. It realises requirement FR6.
- **Responsibilities.** Container images for U2, U4 and U5 and the PostgreSQL container; the Compose file; where secrets are kept (server files or Docker secrets); health checks; logging to standard output for the central logging; how images get to the server through the internal registry; the data volume for the database; and the upgrade and return steps. [FR6.1 to FR6.6, NFR3, NFR6, NFR8]
- **Boundaries.** Holds no business logic. The existing Artifactory, Keycloak, container registry and central logging are outside it.
- **Implementation notes.** No part may pull from the internet while running. Previous image tags are kept so the earlier version can be started again.
- **Size reasoning.** M: no code logic but many details that must be exactly right.

## Coverage Of Building Blocks

| Building block | Unit |
|----------------|------|
| SignIn | U6 |
| PackageSource | U6 |
| ImportClient | U6 |
| ImportService | U4 |
| ArtifactoryGateway | U4 |
| Retention | U4 |
| Catalog | U2 |
| Portal | U5 |
| ArtifactoryStandIn | U3 |

Every one of the nine building blocks is in exactly one unit. U1 and U7 carry shared code and hosting, which belong to no single block.
