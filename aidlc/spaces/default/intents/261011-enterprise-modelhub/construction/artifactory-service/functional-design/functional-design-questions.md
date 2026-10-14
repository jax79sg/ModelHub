# Functional Design Questions: artifactory-service

Context: `artifactory-service` is the one container that touches Artifactory. It receives a verified package from the CLI (contract C1), checks it again, decides whether to skip, finish or fully import it, uploads with `jf hf upload`, records through the Catalog (contract C2), keeps the trusted-key list, and runs retention (contract C4). It reaches model information only through the Catalog (ADR-002). Its requirements are FR1.1, FR1.3 to FR1.8, FR1.12, FR1.14, FR4.2, FR4.3, FR5 to FR5.7 and NFR4 (an import can be stopped at any moment and repeated). The interface, error codes and states are already fixed in C1; these questions are about the decisions behind them.

## Q1. How does the service decide that Artifactory "holds the files" of a model?

Why we ask: this decides skip, finish or full import (FR1.4 to FR1.6). Artifactory is the source of truth for files.

- Option A, list the version in Artifactory and compare every file's path, size and SHA-256 with the signed manifest; it holds the files only if the whole set matches. Pros: exact; catches a missing or changed file. Cons: one listing call per import (small cost); depends on the listing the gateway discovers (open question X1).
- Option B, check only that the version exists. Pros: one cheap call. Cons: a version with a missing file counts as complete.
- Recommendation: A.

A. Option A: list and compare every file against the manifest
B. Option B: the version exists
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. What if Artifactory holds only some of a model's files, or different files?

Why we ask: the upload is meant to be all-or-nothing, so a partial or different set means something unexpected (an earlier failure, a manual change). The service must never overwrite (FR1.8), but deleting is a destructive act.

- Option A, fail the import with a clear message (code `artifactory_inconsistent`) naming what differs, delete nothing, and leave it for an administrator to fix on the Artifactory. Pros: safe; nothing is destroyed without a person deciding. Cons: needs a person to act.
- Option B, delete the incomplete version in Artifactory and upload again. Pros: self-healing. Cons: the service deletes files it did not create this time; a mistake in the comparison deletes good data.
- Recommendation: A.

A. Option A: fail with a clear message, delete nothing
B. Option B: delete the incomplete version and upload again
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. May a version that retention removed be imported again?

Why we ask: after an administrator removes a version, the Catalog refuses a new record for the same model and commit (409, rule BR1.2 of the Catalog design). Someone may still want that model back.

- Option A, refuse: the CLI is told the version was removed by retention (code `removed_by_retention`) and cannot be imported again. Pros: no change to the Catalog; the removal is final. Cons: a model can never come back at the same commit.
- Option B, allow it: the Catalog is changed so that a new record for a removed version is accepted and makes it `imported` again, with its documents stored again, a new trail row, and its age counted from the new import. Pros: a removal is not a dead end; the trail shows both events. Cons: changes an approved Catalog rule (BR1.2 and BR1.12 get an exception) and a state change (`removed` to `imported`).
- Recommendation: B.

A. Option A: refuse
B. Option B: allow, with a Catalog change
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q4. How many imports may run at once?

Why we ask: each import holds received pieces on disk (about the model's size) and uploads over the network. A per-model lock already stops two imports of one model (FR1.12). Two imports of different models are allowed by the contract.

- Option A, no limit beyond the per-model lock. Pros: simplest. Cons: several 100 GB models at once can fill the disk (NFR7).
- Option B, a limit on imports running at once (default 2, a setting); an import that cannot start is told to wait (code `service_busy`, retryable), and the CLI retries by its normal schedule. Pros: bounded disk and bandwidth. Cons: one more rule and one more answer to test.
- Option C, one import at a time. Pros: simplest disk bound. Cons: a long import blocks every other person.
- Recommendation: B.

A. Option A: no limit beyond the per-model lock
B. Option B: a limit (default 2) with a retryable "busy" answer
C. Option C: one import at a time
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q5. Where does the service keep its own records?

Why we ask: the service must remember import jobs and locks, the trusted-key list, the retention setting, and retention decisions (keep or remove, who, when). None of that is model information, so it does not belong in the Catalog (ADR-002, ADR-003), and the service needs somewhere durable to keep it (NFR4).

- Option A, its own schema in the same PostgreSQL container, with its own database user that cannot see the Catalog's tables (and the reverse). Pros: one database to run, back up and upgrade; transactions across the service's own records; separation enforced by database permissions. Cons: both services depend on the same database container being up.
- Option B, a small file database (SQLite) on a volume only this container uses. Pros: fully separate. Cons: a second thing to back up; harder to run two copies later; separate upgrade steps.
- Option C, put these records in the Catalog. Pros: one store. Cons: breaks the idea that the Catalog holds only model information, and makes every retention decision a Catalog call.
- Recommendation: A.

A. Option A: its own schema and user in the same PostgreSQL
B. Option B: SQLite file on its own volume
C. Option C: in the Catalog
D. Not yet defined
X. Other (please specify)

[Answer]: A
