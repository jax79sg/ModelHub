# Rules: artifactory-service

The decisions the service makes. Sources are requirement, contract and decision IDs and the answers in `functional-design-questions.md` (FDQ). Error codes and states are those of contract C1.

```yaml
unit: artifactory-service
rules:
  - id: BR1.1
    statement: Import calls need a valid personal import token; retention and key calls need an administrator; each is refused otherwise and nothing changes.
    category: authorization
    applies_to: [ImportJob, TrustedKey, RetentionSetting, RetentionDecision]
    trigger: any call
    logic: "Calls under /imports present a personal token. The service asks the Catalog to check it; inactive gives 401 token_invalid with a message that says to make a new token when the reason is revoked or expired and says nothing else. A personal token is accepted only under /imports. Retention, setting and key calls need a Keycloak token of a person with the administrator role (common rule); a signed-in person without it gets 403 forbidden and no change is made. The owner of an ImportJob is the person the token belongs to, and only that person may read, send pieces to, start or cancel their own job."
    violation: 401 or 403
    source: [FR4.2, FR4.3, FR1.2, AC4.1]
  - id: BR1.2
    statement: Before anything is received, the names are checked against Artifactory's rules and the signature against the trusted keys.
    category: validation
    applies_to: [ImportJob]
    trigger: POST /imports
    logic: "Split modelId into organisation and model. Refuse with 422 name_rule_broken (naming the field and the rule) IF the organisation is not letters, numbers and single hyphens, or starts or ends with a hyphen, or is all digits; or the model has anything other than letters, numbers, hyphen, underscore and period; or the commit (the revision) has anything other than letters, numbers, hyphen and period or is not 40 hexadecimal characters. Parse bundleDescription; IF it names a different modelId or commit than the request THEN 422 bad_description. Check bundleSignature over the description with every key in TrustedKey that is not revoked: no key matches by fingerprint gives 422 untrusted_signing_key; a matching key whose signature does not verify gives 422 bad_signature. Nothing is stored for a refused call."
    violation: 422
    source: [FR1.7, FR1.14, AC1.6, AC1.10]
  - id: BR1.3
    statement: At creation the service decides skip, finish, repair or full import from what Artifactory holds and what the Catalog holds.
    category: policy
    applies_to: [ImportJob]
    trigger: POST /imports, after BR1.2 and BR1.9
    logic: "Ask the gateway to list the version in Artifactory and compare every file's path, size and SHA-256 with the signed manifest (complete only if all match: FDQ1 A). Ask the Catalog for the version's state. Then: complete in Artifactory AND Catalog imported -> plan skip, state skipped, outcome skipped, answer 200, and have the Catalog add one trail row with outcome skipped; no pieces are needed. Complete in Artifactory AND Catalog none or removed -> plan finish (outcome completed: the files are not uploaded again, but the pieces are still sent because the Catalog record needs the documents inside the bundle). Not in Artifactory (nothing listed) AND Catalog imported -> plan repair (upload again, keep the record, add one trail row with outcome repaired). Not in Artifactory AND Catalog none or removed -> plan full. Something listed that is partial or different -> fail with 409 artifactory_inconsistent naming the differences, delete nothing, retryable false (FDQ2 A)."
    violation: 409 artifactory_inconsistent
    source: [FR1.4, FR1.5, FR1.6, AC1.2, AC1.4, AC1.5, FDQ1 A, FDQ2 A, FDQ3 B]
  - id: BR1.4
    statement: Each piece is checked against the signed description as it arrives and stored whole or not at all.
    category: validation
    applies_to: [ReceivedPiece]
    trigger: PUT piece
    logic: "IF the index is outside 1 to piece_count THEN 422. IF the body is larger than the description allows for that piece THEN 413 piece_too_large. Write the body to a temporary file while computing its SHA-256 without holding it in memory. IF the SHA-256 differs from both the X-Piece-SHA256 header and the description's value for that index THEN discard it and answer 409 piece_mismatch. Otherwise move it into place in one step and record it; a piece already stored with the same checksum is accepted again with 204. Pieces are accepted only while the state is receiving."
    violation: 409, 413 or 422
    source: [FR1.1, FR1.14, NFR4, NFR7, C1]
  - id: BR1.5
    statement: An import starts only when every piece is present, and starting twice does no harm.
    category: constraint
    applies_to: [ImportJob]
    trigger: POST start
    logic: "IF any piece is missing THEN 409 pieces_missing with the missing indexes. IF the job is already past receiving THEN answer 202 with its state. Otherwise set state ready, then verifying when a running slot is free (BR1.10) and return 202."
    violation: 409
    source: [FR1.1, NFR4, C1]
  - id: BR1.6
    statement: The service joins and unpacks the pieces in order, deleting each as it is used, and checks every file against the signed manifest.
    category: validation
    applies_to: [ImportJob, ReceivedPiece]
    trigger: state verifying
    logic: "Read the pieces in index order and unpack the files to working storage, deleting each piece (consumed true) after it has been unpacked, so disk use stays near one copy of the model. Check every unpacked file's size and SHA-256 against the signed manifest. IF any differs, or a file is missing, or an extra file appears, THEN set state failed with error manifest_mismatch (retryable false), remove all working files, and release the lock. Memory use stays within 8 GB for any file size by streaming."
    violation: failed manifest_mismatch
    source: [FR1.14, AC1.10, NFR7]
  - id: BR1.7
    statement: Files are uploaded with jf hf upload, never overwritten, retried on network errors, and checked afterwards.
    category: policy
    applies_to: [ImportJob]
    trigger: state uploading, plan full or repair
    logic: "Run the upload with the model id as repository id and the commit as revision, the Artifactory token from the secret file, and never the overwrite option. A network error or a timeout is retried up to 5 times waiting 1, 2, 4, 8 and 16 seconds, each with a random extra wait of up to 1 second. IF Artifactory answers 409 THEN fail with artifactory_conflict (retryable false) and leave Artifactory as it is. Any other refusal fails with artifactory_refused (retryable false) and the message the gateway can show without secrets. After a successful upload, list the version and compare it with the manifest as in BR1.3; a difference fails with artifactory_inconsistent. Never log the token or the command line's secret parts."
    violation: failed with the stated code
    source: [FR1.1, FR1.6, FR1.8, FR1.9, AC1.5, AC1.7, AC1.8]
  - id: BR1.8
    statement: The service records through the Catalog only after Artifactory holds the files, and the outcome follows the plan.
    category: constraint
    applies_to: [ImportJob]
    trigger: state recording
    logic: "Plan full or finish: send the version record, its documents and its import record (person, time, computer, bundle name and checksum, signing key fingerprint, tool version, check results) to the Catalog in one call. Plan repair: send an import-only record with outcome repaired. Catalog 200 or 201 -> state done; outcome imported for full, completed for finish and repair. A network error or 5xx is retried as in BR1.7. Catalog 409 record_conflict fails with catalog_conflict (retryable false). Working files are removed when the job ends in any state."
    violation: failed with the stated code
    source: [FR1.3, FR1.5, FR2.3, ADR-002, ADR-006]
  - id: BR1.9
    statement: One import per model at a time; a repeated create returns the unfinished import; an idle import is cancelled after 24 hours.
    category: constraint
    applies_to: [ModelLock, ImportJob]
    trigger: POST /imports; every hour
    logic: "The lock key is the model id in lower case. IF a lock exists held by an unfinished import of the same commit by the same person THEN return that import (201 with its missing pieces). IF it is held by any other import THEN 409 model_locked naming the model. The lock is taken when the job is created and released when it ends in done, failed, cancelled or skipped. An import not finished whose last_activity_at is more than import_idle_hours old (default 24) is cancelled, its working files removed and its lock released."
    violation: 409 model_locked
    source: [FR1.12, AC1.9, NFR4, C1]
  - id: BR1.10
    statement: At most a set number of imports may be verifying, uploading or recording at once; further ones are asked to wait.
    category: constraint
    applies_to: [ImportJob]
    trigger: POST start
    logic: "max_running_imports defaults to 2 and is a setting of at least 1. IF the number of jobs in verifying, uploading or recording is at the limit THEN answer 503 service_busy with retryable true and leave the job in receiving with its pieces."
    violation: 503 service_busy
    source: [NFR7, FDQ4 B]
  - id: BR1.11
    statement: An import can be cancelled, and a restart leaves no half-run import behind.
    category: constraint
    applies_to: [ImportJob]
    trigger: DELETE import; service start-up
    logic: "DELETE on an import not yet ended: set state cancelled, remove all received pieces and working files, release the lock, answer 204; on an ended or unknown import answer 204. At service start-up every job in verifying, uploading or recording is set to failed with error interrupted (retryable true), its working files and unconsumed pieces are removed and its lock released; the CLI's rerun is then decided afresh by BR1.3, so what was already uploaded is finished, not uploaded again."
    violation: not applicable
    source: [NFR4, FR1.5, FR1.12, C1]
  - id: BR1.12
    statement: Progress is readable at any time and no message ever holds a secret.
    category: policy
    applies_to: [ImportJob]
    trigger: GET import
    logic: "Return state, outcome, pieces missing, the step, bytes done and total and the update time, and the error with code, message and retryable. Messages are made from fixed texts and names (model id, rule broken, file path), never from raw output of the upload tool or Artifactory, which are logged after secrets are redacted."
    violation: not applicable
    source: [FR1.11, FR1.13, NFR5b, C1]
  - id: BR1.13
    statement: Trusted keys are managed by administrators, and a key is added only when the person types back its fingerprint correctly.
    category: authorization
    applies_to: [TrustedKey]
    trigger: add, list or revoke key
    logic: "Add: the administrator supplies the public key, a label of 1 to 80 characters and the fingerprint they have confirmed. The service computes the fingerprint of the key; IF it differs from the typed one (ignoring case and separators) THEN 422 fingerprint_mismatch and nothing is added. A key already present answers 409. Revoke sets revoked_at; bundles signed by a revoked key are refused from then on (BR1.2), and imports already done are not affected. List shows fingerprint, label, who added it and when."
    violation: 422 or 409
    source: [FR1.14, FR4.2, AC1.10]
  - id: BR1.14
    statement: The retention period is a setting of 1 to 3650 days, 365 by default, that only administrators change.
    category: policy
    applies_to: [RetentionSetting]
    trigger: read or change of the setting
    logic: "A change outside 1 to 3650 is refused with 422. A change takes effect at once for the next listing and does not alter past decisions."
    violation: 422
    source: [FR5.1, FR4.2]
  - id: BR1.15
    statement: The retention list shows imported versions older than the period, counted from the later of their import time and the last keep decision.
    category: calculation
    applies_to: [RetentionDecision]
    trigger: GET retention list
    logic: "Administrators only. Ask the Catalog for versions in state imported imported before now minus the period, oldest first. For each, take the latest keep decision for that model and commit (if any); IF its time is after now minus the period THEN leave the version out. Return model id, commit, import time, importer, size and the last keep time if any."
    violation: 403 for a non-administrator
    source: [FR5.2, FR5.3, FR5.4, AC5.1]
  - id: BR1.16
    statement: A version is removed only after an administrator decides, for that version, each time.
    category: authorization
    applies_to: [RetentionDecision]
    trigger: POST decision
    logic: "Administrators only. A decision names one model id and commit and is keep or remove; there is no call that decides several versions at once. Keep: store the decision (outcome done) and the version leaves the list until the period passes again. Remove: follow BR1.17. A decision for a version not in state imported is refused with 409. The decision records who and when."
    violation: 403 or 409
    source: [FR5.4, FR5.7, FR4.3, AC4.1]
  - id: BR1.17
    statement: Removing deletes from Artifactory first, then marks the version removed in the Catalog, and a failure at either step leaves it listed and retryable.
    category: constraint
    applies_to: [RetentionDecision]
    trigger: a remove decision
    logic: "Store the decision with outcome failed. Ask the gateway to delete the version's files in Artifactory (a 404 meaning already gone counts as deleted). IF the deletion fails THEN keep outcome failed with a message and do not call the Catalog; the version stays in the list and the administrator may decide again. IF it succeeds THEN call the Catalog's removal. IF that succeeds THEN set outcome done. IF it fails THEN set outcome files_deleted_not_marked; the next remove decision for this version repeats only the Catalog step."
    violation: failed or files_deleted_not_marked
    source: [FR5.5, FR5.6, AC5.2]
  - id: BR1.18
    statement: Every retention decision is part of the trail with who and when, and is never changed afterwards except for its outcome.
    category: policy
    applies_to: [RetentionDecision]
    trigger: any decision; GET decisions
    logic: "Decisions are listable newest first, filtered by model and person, for the portal to merge into the trail view (contract C4). No call edits or deletes a decision; only the outcome field changes, by BR1.17."
    violation: not applicable
    source: [FR5.7, ADR-007, C4]
  - id: BR1.19
    statement: Only this service calls Artifactory, with the one service credential from the secret file, and never builds a storage path.
    category: constraint
    applies_to: [ArtifactoryVersionListing]
    trigger: any Artifactory call
    logic: "Every call goes through the gateway. The credential comes from the artifactory_token secret and is never logged. Storage locations of a version are found by listing; the gateway never composes a path from a layout assumption, and when listing returns nothing it reports 'not present'. Timeouts: connect 5 seconds, read 30 seconds, upload no progress for 10 minutes."
    violation: not applicable
    source: [C5, X1, FR6.4]
  - id: BR1.20
    statement: A new import is refused with a retryable answer when the disk could not hold it.
    category: constraint
    applies_to: [ImportJob]
    trigger: POST /imports
    logic: "Add the sizes in the description plus 10 percent. IF the free space on the receiving storage is smaller THEN 507 insufficient_storage with retryable true and nothing stored."
    violation: 507
    source: [NFR7, NFR4]
  - id: BR1.21
    statement: The service's own tables change by versioned steps that keep data, applied at start-up under a lock, and the service refuses a database newer than itself.
    category: constraint
    applies_to: [ImportJob, TrustedKey, RetentionDecision]
    trigger: service start-up
    logic: "As for the Catalog: apply pending steps in order under a database lock, record each, refuse to start on an unknown newer step. The service's database user can reach only its own schema."
    violation: refuse to start
    source: [FR6.6, AC6.2, FDQ5 A]
  - id: BR1.22
    statement: A program that is too old for the service is told so with 426 and nothing is done.
    category: constraint
    applies_to: [ImportJob]
    trigger: any call under /imports
    logic: "Read X-Modelhub-Client. IF it is missing or older than the oldest version the service supports (a setting, min_client_version) THEN answer 426 with a message naming the version to update to and change nothing."
    violation: 426
    source: [C1 versioning, import-cli BR1.14]
```

## Rules Summary

| ID | Rule | Category |
|----|------|----------|
| BR1.1 | Who may call | authorization |
| BR1.2 | Names and signature checked at create | validation |
| BR1.3 | Skip, finish, repair or full | policy |
| BR1.4 | Pieces checked as they arrive | validation |
| BR1.5 | Start when complete; idempotent | constraint |
| BR1.6 | Unpack in order; check manifest | validation |
| BR1.7 | Upload, never overwrite, retries | policy |
| BR1.8 | Record through Catalog after upload | constraint |
| BR1.9 | Per-model lock; 24 h idle | constraint |
| BR1.10 | Running limit | constraint |
| BR1.11 | Cancel; restart leaves no half-run | constraint |
| BR1.12 | Progress without secrets | policy |
| BR1.13 | Trusted keys | authorization |
| BR1.14 | Retention setting | policy |
| BR1.15 | Retention list | calculation |
| BR1.16 | Decision per version | authorization |
| BR1.17 | Delete then mark | constraint |
| BR1.18 | Decisions in the trail | policy |
| BR1.19 | One gateway; discover paths | constraint |
| BR1.20 | Disk check | constraint |
| BR1.21 | Own schema upgrades | constraint |
| BR1.22 | Too-old program gets 426 | constraint |
