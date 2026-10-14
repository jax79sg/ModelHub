# Architecture Decisions

Decisions made in Domain Design. "DQ" is `domain-design-questions.md`. The building blocks are in `components.md`. Each decision lists its context, what was chosen, its consequences and the alternatives rejected.

## ADR-001: A server-side import service does the upload and recording

- **Context.** The requirements had the CLI upload to Artifactory with `jf hf upload` (FR1.1, FQ9 A). That needs the JFrog CLI, Python 3 and a `huggingface_hub` no newer than 1.19.0 on every import computer, while the CLI needs 2.2 or newer (risk R1). In intent capture you listed an "import service" among the containers (IQ9 A). The owner chose between the CLI doing everything and a server-side service (DQ1).
- **Decision.** A server-side ImportService receives each verified package from the CLI, checks it again, decides skip, repair or full import, uploads through the ArtifactoryGateway and records through the Catalog. The CLI (ImportClient) verifies, signs the person in, sends the package, and reports. This was chosen against the recommendation, which was to let the CLI do everything (DQ1 B).
- **Consequences.**
  - Positive: the older Python environment and the JFrog CLI live once, in a container, instead of on every import computer; risk R1 is largely removed; the decision rules live in one place; the trail's "who" and "signing key" are checked on the server.
  - Negative: one more container to run and secure; the CLI must send very large files (over 100 GB) to the service, which needs a transfer design (OQ2, OQ5); the service holds the Artifactory upload rights.
  - Neutral: several approved requirements read "the CLI uploads" and need to be updated (see "Effects On Approved Documents" below).
- **Alternatives Rejected.** The CLI does the whole import (DQ1 A, the recommendation): rejected because the owner preferred keeping the older environment off the import computers.

## ADR-002: The Catalog is the only reader and writer of model information

- **Context.** The importer (now the ImportService) and the portal both need model information, and the requirements put database passwords on the server only (FR6.4). The owner chose a data interface that checks the Keycloak token (DQ2 A, DQ3 A).
- **Decision.** The Catalog owns model information, stored documents and the import trail. The ImportService and the Portal reach them only through the Catalog, never the database. The ImportService and Retention keep only their own records (import jobs and trusted keys; the retention setting and decisions) in their own tables of the same PostgreSQL.
- **Consequences.** Positive: one set of rules and queries (filters, sort, search); one place that checks tokens and roles; the version and its trail row are stored in one transaction (FR2.5). Negative: the portal and the importer depend on the Catalog being up; a query that is slow in the Catalog is slow everywhere. Neutral: the Catalog's interface becomes a contract in the next stage.
- **Alternatives Rejected.** The importer or the portal writing the database directly (DQ2 B, DQ3 B): a database login on import computers, "who" self-reported, and the rules copied twice.

## ADR-003: Retention is its own building block

- **Context.** Retention decides, deletes files from Artifactory, then marks the version removed (FR5). The owner chose between its own block and part of the Catalog (DQ4).
- **Decision.** Retention is a separate component. It owns the retention setting and each keep-or-remove decision, deletes through the ArtifactoryGateway, then asks the Catalog to mark the version removed. If the deletion fails nothing is marked (FR5.6).
- **Consequences.** Positive: the Catalog never holds deletion rights over Artifactory; the destructive step is isolated and testable against the stand-in. Negative: the two-step delete-then-mark lives in Retention, so a crash between the steps leaves a version deleted but not marked (a repair rule is needed in functional design). Neutral: one more block.
- **Alternatives Rejected.** Retention inside the Catalog (DQ4 B): mixes information with a destructive action.

## ADR-004: One Artifactory gateway for the whole system

- **Context.** With ADR-001 both the upload and the inspect-and-delete run on the server, and both must apply Artifactory's naming and layout rules (FR1.7). The owner chose between one block and two (DQ5).
- **Decision.** The ArtifactoryGateway is the one place that talks to Artifactory. It uploads with `jf hf upload` and inspects and deletes through Artifactory's web interface.
- **Consequences.** Positive: the naming rules, layout and quirks are written once; the stand-in has one thing to be tested against; JFrog changes (risk R8) touch one block. Negative: the one block carries two kinds of call and the dependency on the JFrog CLI and an older Python. Neutral: both callers run in the server's containers.
- **Alternatives Rejected.** Two blocks (DQ5 B): the rules would be written twice and could drift apart.

## ADR-005: The import service re-verifies the bundle itself

- **Context.** The CLI verifies a bundle on the import computer as it does today. With ADR-001 the server receives the files afterwards. Security is a top quality (SQ6 A), and the trail records the signing key (FR2.3). The owner chose who verifies (DQ6).
- **Decision.** The CLI verifies first, so it fails fast, and the ImportService verifies again: the signature against its own trusted-key list and every file against the signed manifest, before uploading. The service owns the trusted-key list (the TrustedKey entity).
- **Consequences.** Positive: a changed or unsigned file cannot be imported by a modified or misused CLI; the signing key in the trail is checked on the server. Negative: the service needs its own trusted-key list and the checking code (reused from the CLI's library), and the checking runs twice; keys must be added to the service by someone (OQ3). Neutral: a new requirement follows (see below).
- **Alternatives Rejected.** The CLI only (DQ6 A): the service would trust whatever an authenticated CLI sends.

## ADR-006: Artifactory is the source of truth for files, the Catalog for information

- **Context.** Two stores can disagree after a half-finished import (risk R9). Requirements FR1.5 and FR1.6 already say what to do in each case.
- **Decision.** Artifactory is the source of truth for a version's files. The Catalog is the source of truth for the model information and the trail. The ImportService compares the two before acting and repairs the side that is missing.
- **Consequences.** Positive: every disagreement has one answer. Negative: a version whose files are removed from Artifactory outside this system (by an Artifactory administrator) stays recorded as imported until a check finds it; a reconciling check is a later option, not planned.
- **Alternatives Rejected.** Treating the Catalog as the source of truth for files: it holds no files, only descriptions of them.

## ADR-007: The trail is split by who writes it, and viewed as one

- **Context.** The trail records imports (FR2.3) and retention decisions (FR5.7). An import's trail row must be written in the same transaction as the version (FR2.5).
- **Decision.** The import-trail row (ImportRecord) is owned by the Catalog, so it lands in the same transaction as the version. Each retention decision (RetentionDecision) is owned by Retention. The portal shows both together as one trail.
- **Consequences.** Positive: no transaction spans two components. Negative: the combined trail is a read that joins two owners; deleting a version's files and recording the decision are not in one transaction (see ADR-003). Neutral: the trail's accepted weakness (ordinary rows, RQ11 A) applies to both.
- **Alternatives Rejected.** Everything in one Trail component: rejected because it would need a transaction across the Catalog and Trail for every import (the aggregate-boundary rule: no transaction across two components).

## ADR-008: The import service keeps a job record for each import

- **Context.** An import can be stopped at any moment and must be safe to run again (NFR4), and two imports of one model must not run together (FR1.12).
- **Decision.** The ImportService owns an ImportJob for each import (model, commit, state, who started it, when). The job's state and a per-model lock let a repeated import see what was done and carry on, and make the second concurrent import stop at once.
- **Consequences.** Positive: restart and locking have an owner and a place to be tested. Negative: the job record is a new thing to store and to clean up. Neutral: how long jobs are kept is for functional design.
- **Alternatives Rejected.** Working out the state each time from Artifactory and the Catalog alone: no place to hold a lock or to show an import in progress.

## ADR-009: The Artifactory stand-in is a test-only component

- **Context.** No real Artifactory is available (IQ17), the stand-in must not be delivered (IQ24 A), and the documented behaviour is only a starting point (IQ23 B).
- **Decision.** ArtifactoryStandIn is a separate component that nothing in the delivered system depends on. It records every behaviour it assumes and keeps a checklist to confirm on a real Artifactory (FR7).
- **Consequences.** Positive: tests run with no Artifactory; the assumptions are visible and reviewable. Negative: its fidelity is only as good as JFrog's documentation (risks R2, R3). Neutral: it needs its own tests to keep it honest.
- **Alternatives Rejected.** Testing only with recorded responses: cannot exercise the upload and delete flows.

## ADR-010: The system issues its own personal tokens for the CLI

- **Context.** The import computer may have no web browser or internet, so the CLI cannot sign a person in with Keycloak the usual way. In Contract Design the owner chose a personal token made in the portal (CQ4 C) and chose that the system issues and checks its own tokens (CQ7 B), both against the recommendations (device sign-in; Keycloak-issued offline tokens).
- **Decision.** The Catalog owns a PersonalToken for each token: a signed-in person makes one in the portal, it is shown once, only a hash is stored, it works for importing only, it expires (default 90 days) and it can be revoked at once by its owner or an administrator. The import service checks a token by asking the Catalog. The CLI keeps the token in a file only its owner can read. Keycloak still signs people in to the portal and says who is an administrator.
- **Consequences.**
  - Positive: works on a browserless, offline computer; "who" is the person the token was made for; revocation and expiry are under the system's control; no dependency on Keycloak offline-token settings.
  - Negative: a second token system to build and defend (generation, hashing, expiry, revocation, a safe comparison, no leaks to logs); a long-lived secret on import computers; the Catalog is now on the path of every import's first step (a Catalog outage stops imports).
  - Neutral: new requirements FR4.4 to FR4.6 and the Catalog's PersonalToken entity; the portal gets a token page.
- **Alternatives Rejected.** Device sign-in (CQ4 A), the recommendation: needs another device with a browser that can reach Keycloak. A Keycloak-issued offline token (CQ7 A), the recommendation: Keycloak would stay the only issuer, but needs Keycloak administrators to allow offline tokens and set their lifetime. Typing username and password into the CLI (CQ4 B): Keycloak discourages that mode and the password passes through the CLI.

## Effects On Approved Documents

ADR-001 and ADR-005 change what some already-approved requirements and risks say. These are listed here and applied in the documents, so the owner can see them at this stage's approval:

| Document | What changes | Why |
|----------|--------------|-----|
| `requirements.md` FR1.1 | The CLI hands the verified package to the import service, which uploads with `jf hf upload`; the CLI no longer uploads | ADR-001 |
| `requirements.md` FR1.2, FR1.3 | The CLI signs the person in and sends the token to the import service; the import service records through the Catalog | ADR-001, ADR-002 |
| `requirements.md` FR1.12 | The lock is held by the import service | ADR-008 |
| `requirements.md` new FR1.14 | The import service checks the bundle's signature against its own trusted keys and every file against the signed manifest before uploading; administrators manage that key list | ADR-005 |
| `requirements.md` CT6, A2, NFR10 | The JFrog CLI, Python 3 and the older `huggingface_hub` are needed on the server, not on import computers | ADR-001 |
| `raid-log.md` R1 | Largely removed: the older environment lives once, in a container | ADR-001 |
| `requirements.md` new open question | How a very large package is sent to the import service | ADR-001 |
