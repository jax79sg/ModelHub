# Requirements

Inputs: `intent-statement` and `scope-document` (from `ideation/`), the feasibility documents, and your answers in `requirements-analysis-questions.md` (written RQ). Earlier answers are written IQ (`intent-capture-questions.md`), FQ (`feasibility-questions.md`) and SQ (`scope-definition-questions.md`). Constraint, risk and evidence references (CO, CT, CR, R, E) are in `constraint-register.md`, `raid-log.md` and `feasibility-assessment.md`.

## Intent Analysis

**Goals, not just features.**

1. Many people across the organisation can find and fetch the models the organisation has imported, instead of the models sitting in one folder on one computer. [IQ1]
2. Every import leaves proof of who brought in what, when, from which bundle and under which signing key. [IQ1, IQ3, RQ2, RQ14]
3. Artifactory stays the home of the model files and of fetching them with standard tools; a database holds the information Artifactory does not. [IQ6, IQ7, feasibility E10]
4. The new parts are easy to host: Docker containers on one Linux server that has no internet access. [IQ9, IQ10, FQ8]
5. The work can be designed and built although no real Artifactory is available. [IQ17]

**Classification.** An enhancement of an existing tool plus the replacement of its storage (a folder becomes Artifactory and a database). It touches four components (the CLI, the web app, a database and the hosting), with a clear gap in knowledge (the real Artifactory). Depth: comprehensive.

**How the existing tool is used.** The existing contracts are kept where they still apply: the download record (C1), the bundle (C2) and the summary file (C3). What the CLI reads from a verified bundle is exactly what the existing `unpack` writes today. The CLI's exit statuses (0 all fine, 1 an item failed, 2 could not run) and its retry waits (1, 2, 4, 8, 16 seconds) are kept for the same reasons as before.

## Functional Requirements

### FR1 Importing a model

- FR1.1 After the CLI has verified a bundle (the signature is by a trusted key and every piece is intact), the CLI hands the verified package to a server-side import service, which uploads the model's files to a local Hugging Face repository in Artifactory with `jf hf upload`, using the model id as the repository id and the full commit hash as the revision. [IQ6 A, FQ9 A, CT-8, E2; changed by DQ1 B, ADR-001]
- FR1.2 Before importing, the person has a personal token made in the portal (FR4.4). The CLI sends it to the import service, which checks it with the Catalog. The person the token was made for is recorded as who imported the model. [RQ4 A, CQ4 C, CQ7 B; changed by ADR-001, ADR-010]
- FR1.3 In the same import the import service records the model information and one import-trail row in the database, through the Catalog (FR2). [IQ6 A, RQ14 A; changed by DQ2 A, ADR-001, ADR-002]
- FR1.4 If the same model id and the same commit are already imported (their files are in Artifactory and their record is in the database), the CLI skips that model, says so in its report with the model id and the commit, and carries on with the rest of a list. A skip is not a failure. [FQ10, FQ13 B]
- FR1.5 If Artifactory already holds the model's files but the database has no record of it, the CLI finishes the missing database part without uploading the files again and says so in its report. [RQ5 A, R9]
- FR1.6 If the database has a record but Artifactory does not hold the files, the CLI treats the import as incomplete, uploads the files again, keeps the database record, and says so in its report. Artifactory is the source of truth for the files and the database is the source of truth for the information and the trail. [corner checklist: two copies of one fact; R9]
- FR1.7 Before uploading, the CLI checks the model's names against Artifactory's rules: organisation names use letters, numbers and single hyphens and neither start nor end with a hyphen; model names use letters, numbers, hyphens, underscores and periods; revisions use letters, numbers, hyphens and periods. A model that breaks a rule is reported by name with the rule it broke, and the import carries on with the others. [CT-11, E5, R4]
- FR1.8 The CLI never asks Artifactory to overwrite an existing version. If Artifactory answers that the version exists (409), the model is reported as failed with that reason. [CT-12, E6, R5]
- FR1.9 A network error while sending a package to the import service, or while the import service uploads to Artifactory, is retried up to 5 times, waiting 1, 2, 4, 8 and 16 seconds, each with a small random extra wait. After that the model is marked failed and the run carries on with the others. [existing retry rule; changed by ADR-001]
- FR1.10 The CLI ends with status 0 when every model was imported or skipped, 1 when at least one model failed, and 2 when it could not run at all (for example sign-in failed). [existing contract C4]
- FR1.11 The CLI's report lists each model as imported, skipped, completed (a half-finished import finished) or failed with a reason, and never prints a token or password. [the existing tool's error-reporting and secrets rules; RQ12 A]
- FR1.12 Two imports of the same model at the same time are not allowed: the import service holds a lock for each model, and the second import stops with a message naming the model. [corner checklist: concurrency; existing run lock; changed by ADR-008]
- FR1.13 Any step that takes longer than 2 seconds shows live progress. [existing NFR1.5]
- FR1.14 Before uploading, the import service checks the bundle's signature against its own list of trusted signing keys and every file against the signed manifest, and refuses a bundle that fails either check. Administrators manage the list of trusted keys, and a key is added only after the person confirms its fingerprint. [DQ6 B, ADR-005, existing NFR2]

### FR2 Recording the information

- FR2.1 For each imported model version the database holds: model id, commit, capture time; licence, language, tags, task and library; the downloads and likes counts and size with the time they were captured; created and last-modified times; the file list with each file's size, checksum, file type and Hugging Face's safety-scan result; and the commit history, branches and tags. [IQ7, existing summary file C3]
- FR2.2 The database also holds the model's README (original and the copy with pictures stored locally), the pictures, the Hugging Face responses saved as they came, the checksum manifest and the signed bundle description files. [RQ1 A]
- FR2.3 Each import adds one import-trail row holding: who imported it, when (UTC), on which computer, the bundle's name and checksum, the fingerprint of the key that signed it, the tool version, and the result of the checks made before the upload. [RQ2 B, RQ14 A, IQ3 B]
- FR2.4 A value Hugging Face did not give is stored as empty (null), never as 0 or an empty text, so "unknown" and "zero" stay distinct. [existing rule C3]
- FR2.5 The version record, its files, its pictures and its trail row are written in one transaction: either all are stored or none are. [corner checklist: multi-step write]
- FR2.6 Fields in the saved summary that the importer does not know are kept (inside the saved Hugging Face responses and summary) and do not stop the import. [existing rule: additive change only]
- FR2.7 The licence name is kept and shown with the model; a licence file, when the model has one, is stored too. A model with no licence is stored with an empty licence and shown as "no licence given". [FQ3 A, CR-1]
- FR2.8 A model with no README, a file listed but never downloaded, and a README picture that could not be fetched are each stored as such and shown as such. [existing prototype behaviour]

### FR3 The portal

- FR3.1 Every portal page requires a Keycloak sign-in; a person who is not signed in sees only the sign-in. [IQ8 A, IQ16 B, IQ21 A]
- FR3.2 The portal reads the database, not a folder. [IQ8 A, SQ7 A]
- FR3.3 The portal keeps today's prototype features: the models list with filters (task, library, licence, language, parameter size) and sort, 30 models per page, the model card, files and versions, commit history, the revision menu, and the dark and light themes. [SQ7 A]
- FR3.4 People can filter and sort the models list by when a model was imported and by whom. [RQ6 A]
- FR3.5 People can search the text of model cards. [RQ6 B]
- FR3.6 Each model's page shows how to fetch it from Artifactory with standard tools: the repository address, the model id and the revision, and a link to Artifactory. The portal does not serve the model files itself. [IQ8 A, IQ3 C]
- FR3.7 The portal keeps its safe rendering: model-card text is sanitised, nothing is requested from outside the organisation, and files are never rendered in the portal's own address. [existing prototype hardening]
- FR3.8 If the database is not reachable, the portal says so plainly and shows no stale data. If Keycloak is not reachable, new sign-ins fail with a message, and people already signed in keep working until their session ends. [corner checklist: services down]

### FR4 Access

- FR4.1 Every signed-in person can browse and fetch. There are no other roles for browsing. [RQ3 A]
- FR4.2 One administrator role, held in Keycloak, may change the settings and decide retention (FR5). [RQ13 C]
- FR4.3 A person without the administrator role who tries a settings page or a retention decision is refused with a message, and nothing changes. [RQ13 C; corner checklist: per-object authorization]
- FR4.4 A signed-in person can make a personal token in the portal and give it a name. The portal shows its value once; only a hash of it is stored. [CQ4 C, CQ7 B; ADR-010]
- FR4.5 A personal token works only for importing. It expires after a lifetime an administrator sets (default 90 days). The person who owns it, or an administrator, can revoke it at once. A revoked, expired or unknown token is refused. [CQ7 B; ADR-010; defaults are assumption A11]
- FR4.6 The portal lists a person's own tokens (name, first characters, created, expires, last used, revoked) and never shows a value again. An administrator can list and revoke any token. [CQ7 B; ADR-010]

### FR5 Retention

- FR5.1 A retention period is a setting. Its default is 1 year, and an administrator can change it. [RQ10 A, FQ3 C]
- FR5.2 A version's age is counted from the time it was imported. [assumption A3]
- FR5.3 Versions older than the retention period are listed for administrators. [RQ9 C]
- FR5.4 For each listed version an administrator decides, each time, to keep it (its age restarts from that moment) or to remove it. Nothing is ever removed without that decision for that version. [RQ9 C]
- FR5.5 Removing a version deletes its files from Artifactory and marks the version removed in the database. The version stays listed as removed and its trail rows stay. [FQ3 C, RQ9 C]
- FR5.6 If deleting from Artifactory fails, the version is not marked removed; the failure is shown and the removal can be tried again. [corner checklist: multi-step write]
- FR5.7 Each retention decision (keep or remove) is added to the import trail with who decided and when. [RQ13 C, IQ3 B]

### FR6 Hosting

- FR6.1 Each new part runs as a container started by Docker Compose on one Linux server that already has Docker. The existing Artifactory, Keycloak, container registry and central logging are outside these containers. [IQ9 A, IQ10 A, FQ8 A, FQ1]
- FR6.2 Container images are built on the internet side and reach the server through the internal container registry. No part downloads anything from the internet while running. [FQ1 A, CT-5]
- FR6.3 The database's data is kept on storage that survives a container restart and an image upgrade. [corner checklist: migration and upgrade]
- FR6.4 Passwords and tokens for Artifactory, the database and Keycloak are kept in files or Docker secrets on the server that only the services can read. None is in an image, a project file, a log or an error message. [RQ12 A]
- FR6.5 Each part writes its logs in a structured form to standard output, and offers a health check, so the central logging and monitoring can collect and poll them. [FQ1 B, SQ2 C]
- FR6.6 An upgrade is: stop the parts, replace the images with newer tagged ones, start them. Database changes are applied by a step that keeps existing data. The previous version's image tags are kept so it can be started again. [SQ6 C, corner checklist: migration and upgrade]

### FR7 The Artifactory stand-in

- FR7.1 A stand-in for Artifactory exists for building and testing. It answers the Hugging Face calls that `jf hf upload`, `snapshot_download` and the libraries make, plus the other Artifactory calls the CLI and the portal need, such as listing a repository and reading file checksums. It is not part of what is delivered. [IQ17, IQ22 B, IQ24 A]
- FR7.2 The stand-in follows JFrog's documented behaviour as its starting point: the naming rules, a 409 answer when a version exists without overwrite permission, and revisions as commit hashes. Every behaviour it assumes is written down. [IQ23 B, R2]
- FR7.3 A short checklist lists each documented behaviour that must be confirmed on a real Artifactory when one is available. [R3]

### FR8 Importing the old folder store (designed now, built after the first version)

- FR8.1 The CLI can import the models already in a model store folder in the existing layout (C3), under the same rules as FR1, FR2 and FR4. [FQ12 A, SQ8 A]

## Non-Functional Requirements

- NFR1 **Findability.** Within 1 hour of an import finishing, the model appears in the portal's list and can be fetched from Artifactory with `snapshot_download`. Pass criterion: measured from the end of the CLI's report to the first successful portal listing and fetch. [IQ15 B]
- NFR2 **Portal speed.** The models list returns in under 1 second, for at least 95% of requests, when the store holds 1,000 models, measured on the server. [RQ7 A, FQ5 (planning figure)]
- NFR3 **Availability.** The system must be available in business hours. It may be down for upgrades and repairs, and no uptime percentage is promised. [RQ8 A]
- NFR4 **Restart.** Stopping an import at any moment and running it again gives a correct, complete result, and no half-finished record is treated as complete. [FR1.5, FR1.6, existing NFR3]
- NFR5 **Security.** (a) Every portal page and every call to the portal's data interface requires sign-in. (b) Secrets never appear in images, project files, logs or error messages. (c) The import trail is ordinary database rows and is not tamper-proof; this is an accepted limit. (d) Model files are served only through Artifactory. [FR3.1, FR6.4, RQ11 A, FR3.6]
- NFR6 **Operability.** Every part writes structured logs and has a health check; one documented upgrade procedure exists and has been run once from an old to a new version and back. [FR6.5, FR6.6, SQ6 C]
- NFR7 **Capacity.** The design is sized for the earlier planning figure: about 1,000 models, up to 10 versions each, some over 100 GB. The steps the CLI controls keep memory at or below 8 GB at their peak for any file size. [FQ5 (planning figure), existing NFR1.3]
- NFR8 **Offline.** No part of the system makes a connection to the internet while running. The online side's `pull` and `bundle` steps keep their existing behaviour. [FQ1, CT-5, existing NFR5]
- NFR9 **Testability.** Every requirement has an automated test written before the code (the team's test-first practice), and the tests run with no real Artifactory by using the stand-in. [team practice, FR7.1]
- NFR10 **Import platforms.** The CLI's import command behaves the same on Linux and Windows import computers, and needs nothing installed there beyond the single-file program or its offline pack. [existing NFR7; changed by ADR-001]

## Acceptance Criteria

Each criterion has a clear pass or fail. They are examples that the later test plan expands, not the whole test list.

- AC1.1 (FR1.1, FR2.3) Given a verified bundle for a model not yet imported, when the person imports it, then the model's files can be fetched from the Artifactory repository at that commit, the database holds its record, and exactly one trail row exists for the import.
- AC1.2 (FR1.4) Given a model and commit already imported, when the person imports the same bundle again, then nothing is uploaded, the report says "skipped" with the model id and commit, and the exit status is 0.
- AC1.3 (FR1.4) Given a list of three models where the second is already imported, when the person imports the list, then the first and third are imported and the second is skipped.
- AC1.4 (FR1.5, NFR4) Given the files of a model are in Artifactory and the database has no record of it, when the person imports it, then no file is uploaded, the database record and trail row are written, and the report says "completed".
- AC1.5 (FR1.6) Given the database holds a model's record and Artifactory does not hold its files, when the person imports it, then the files are uploaded, the existing record is kept, and the report says so.
- AC1.6 (FR1.7) Given a model whose name breaks an Artifactory naming rule, when the person imports a list that includes it, then it is reported by name with the rule broken and the other models are imported.
- AC1.7 (FR1.8) Given Artifactory answers 409 for a version, when the person imports it, then the model is reported failed with that reason, nothing is overwritten, and the exit status is 1.
- AC1.8 (FR1.9) Given the network drops during an upload, when the upload is retried, then up to 5 retries are made with waits of 1, 2, 4, 8 and 16 seconds, after which the model is marked failed and the run continues.
- AC1.9 (FR1.12) Given an import of a model is running, when a second import of the same model starts, then it stops at once with a message naming the model.
- AC1.10 (FR1.14) Given a bundle whose signing key is not in the import service's trusted list, or one of whose files differs from the signed manifest, when the CLI sends it, then the import service refuses it before uploading anything and the report names the reason.
- AC2.1 (FR2.5, NFR4) Given the database write fails midway through an import, when the person looks at the database, then it holds no part of that import's record and no trail row.
- AC2.2 (FR2.4) Given a model with no downloads count from Hugging Face, when the record is stored, then the count is empty and the portal shows "unknown", not 0.
- AC3.1 (FR3.1) Given a person who is not signed in, when they request any portal page, then they are sent to the sign-in and no model information is returned.
- AC3.2 (FR3.4) Given three models imported at different times by two people, when the person filters by one of them and sorts by import time, then only that person's models appear, newest first.
- AC3.3 (FR3.5) Given a model card containing the word "quantized", when the person searches for it, then that model is in the results.
- AC3.4 (FR3.6) Given a model's page, when the person opens the fetch instructions, then they show the repository address, the model id and the revision, and the portal serves no model file itself.
- AC3.5 (FR3.8) Given the database is stopped, when the person opens the portal, then it says the database is unreachable and shows no model data.
- AC4.1 (FR4.3) Given a signed-in person without the administrator role, when they open the settings or decide a retention item, then they are refused and nothing changes.
- AC4.2 (FR4.4, FR4.5) Given a signed-in person who makes a personal token, when they use it to import, then the import is accepted and the trail row names that person; and when they use the same token to open a settings page or decide a retention item, then it is refused.
- AC4.3 (FR4.5, FR4.6) Given a personal token the owner has revoked, when the CLI uses it, then the import is refused with a message to make a new token, and the token's value never appears in a log or in the portal's token list.
- AC5.1 (FR5.3, FR5.4) Given a version imported 13 months ago and a retention period of 1 year, when an administrator opens the retention list, then it is listed, and it is not removed until the administrator chooses "remove".
- AC5.2 (FR5.6) Given Artifactory refuses the deletion, when the administrator removes a version, then the version is not marked removed and the failure is shown.
- AC6.1 (FR6.4) Given the running containers, when their images, environment and logs are searched for the Artifactory token, then it is not found in any of them.
- AC6.2 (FR6.6, NFR6) Given the system running version N, when it is upgraded to N+1 and then returned to N, then the models and trail rows present before are still present.
- AC7.1 (FR7.1, NFR9) Given the stand-in is running, when the CLI's import tests run, then they pass with no real Artifactory reachable.
- NFR-AC1 (NFR2) Given 1,000 models in the store, when the models list is requested 100 times, then at least 95 responses arrive in under 1 second.

## Constraints

- CT1 The new parts run in Docker Compose on one Linux server with Docker installed. [CT-1]
- CT2 The existing Artifactory stays outside the containers and is reached through its Hugging Face repository address. [CT-2]
- CT3 The database is PostgreSQL in a container. [CT-3]
- CT4 Sign-in is Keycloak. [CT-4]
- CT5 Images reach the server through the internal container registry. [CT-5]
- CT6 The upload uses `jf hf upload`, which needs the JFrog CLI, Python 3 and a `huggingface_hub` no newer than 1.19.0 (Xet transfers up to 1.18.0). These live on the server, in the import service's container, and not on the import computers. [CT-8, CT-9, R1; changed by ADR-001]
- CT7 Artifactory's Hugging Face support is limited to download and upload through `jf hf`; Spaces are not supported. [CT-10]
- CT8 A design is needed within about a month. [CO-3]

## Assumptions

All unconfirmed unless an answer is named.

- A1: The real Artifactory behaves as JFrog's documentation says and is version 7.77.1 or newer with a local Hugging Face repository in the Machine Learning layout. [assumption]
- A2: The server can carry the JFrog CLI, Python 3 and a `huggingface_hub` of 1.19.0 or older in the import service's container. [assumption; changed by ADR-001]
- A3: A version's age for retention counts from its import time, and a "keep" decision restarts the age from the moment of the decision. [assumption]
- A4: The earlier planning figure of about 1,000 models with up to 10 versions each, some over 100 GB, holds. [assumption]
- A5: The portal is served over HTTPS using the organisation's certificates. [assumption]
- A6: (replaced by CQ4 C: the CLI uses a personal token made in the portal, so it needs no browser or internet for sign-in.)
- A11: Personal-token defaults are: lifetime 90 days, import use only, shown once, stored only as a hash, revocable at once, and no fixed limit on how many tokens a person holds. [assumption; to confirm]
- A7: "On which computer" is the import computer's host name. [assumption]
- A8: All times are stored in UTC and shown with their zone. [assumption]
- A9: A model's search text is its README and its tags. [assumption]
- A10: The "1 second" in NFR2 is measured over a stable network on the server itself, not including the person's browser. [assumption]

## Out Of Scope

- Private and gated models, and automatic updates of models already imported. [IQ14]
- Scanning imported files for malicious content. [FQ3 (not selected)]
- Datasets and Spaces. [intent statement, CT7]
- Roles other than "signed in" and "administrator". [RQ3 A, RQ13 C]
- Tamper-proof protection of the import trail. [RQ11 A]
- Backup and restore of the database and the stored files (designed later). [SQ2, backlog B9]
- A documented way for pipelines to fetch models other than Artifactory's own download. [SQ2, backlog B10]
- More than one server, and availability beyond business hours. [RQ8 A]

## Open Questions

- (Answered in Contract Design: the CLI signs in with a personal token made in the portal; a large package is sent as the bundle's pieces, one request each; an administrator is a person with the Keycloak realm role `modelhub-admin`.)
- Is there an organisation-wide rule on HTTPS and certificates (A5)? For NFR design.
- What should happen to an import in progress when the person's sign-in expires? For functional design.
- Should the search in FR3.5 match whole words or parts of words, and in which languages? For functional design.

## Traceability

| Requirement | Origin |
|-------------|--------|
| FR1 | IQ6 A, FQ9 A, FQ10, FQ13 B, RQ4 A, RQ5 A, CT-8, CT-11, CT-12, existing C4; FR1.1 to FR1.3, FR1.9, FR1.12, FR1.14 changed or added by DQ1 B, DQ2 A, DQ6 B (`domain-design/decisions.md` ADR-001, ADR-005, ADR-008) |
| FR2 | IQ7 A, IQ3 B, RQ1 A, RQ2 B, RQ14 A, FQ3 A, existing C3 |
| FR3 | IQ8 A, IQ16 B, IQ21 A, SQ7 A, RQ6 A, RQ6 B, IQ3 C |
| FR4 | RQ3 A, RQ13 C; FR4.4 to FR4.6 added by CQ4 C, CQ7 B (`domain-design/decisions.md` ADR-010) |
| FR5 | RQ9 C, RQ10 A, FQ3 C, RQ13 C |
| FR6 | IQ9 A, IQ10 A, FQ1, FQ8 A, RQ12 A, SQ2 C, SQ6 C |
| FR7 | IQ17, IQ22 B, IQ23 B, IQ24 A |
| FR8 | FQ12 A, SQ8 A |
| NFR1 | IQ15 B |
| NFR2 | RQ7 A |
| NFR3 | RQ8 A |
| NFR4 | FR1.5, FR1.6, existing NFR3 |
| NFR5 | RQ11 A, RQ12 A, SQ6 A |
| NFR6 | SQ6 C, FQ1 B |
| NFR7 | FQ5, existing NFR1.3 |
| NFR8 | FQ1, existing NFR5 |
| NFR9 | team practice, IQ17 |
| NFR10 | existing NFR7, CT-8 |
