# Entities: artifactory-service

Inputs: `unit-of-work.md` (U4), `components.md` (ImportService, ArtifactoryGateway, Retention; entities ImportJob, TrustedKey, RetentionSetting, RetentionDecision), `requirements.md` (FR1.x, FR4.2, FR4.3, FR5.x, NFR4, NFR7), contracts C1, C2, C4, C5 and the answers in `functional-design-questions.md` (written FDQ). The service keeps its own records in its own schema of the PostgreSQL container, with its own database user (FDQ5 A). It holds no model information; that is the Catalog's (ADR-002). Disk space for received pieces is working storage, not a record.

```yaml
unit: artifactory-service
entities:
  - name: ImportJob
    description: One attempt to import one model version. Created by the CLI's first call and ended by done, failed, cancelled or skipped.
    attributes:
      - {name: import_id, type: text, required: true, unique: true}
      - {name: model_id, type: text, required: true}
      - {name: commit, type: text, required: true, constraints: "40 hexadecimal characters"}
      - {name: owner_id, type: text, required: true, constraints: "the person the personal token was made for, from the Catalog's token check"}
      - {name: owner_name, type: text, required: true}
      - {name: bundle_name, type: text, required: true}
      - {name: bundle_description, type: text, required: true, constraints: "the signed description exactly as received"}
      - {name: bundle_signature, type: text, required: true}
      - {name: signing_key_fingerprint, type: text, required: true}
      - {name: computer, type: text, required: true}
      - {name: tool_version, type: text, required: true}
      - {name: check_results, type: structured text, required: false}
      - {name: plan, type: text, required: true, allowed: [skip, finish, repair, full], constraints: "decided at creation (BR1.3)"}
      - {name: state, type: text, required: true, allowed: [receiving, ready, verifying, uploading, recording, done, failed, cancelled, skipped]}
      - {name: outcome, type: text, required: false, allowed: [imported, completed, skipped, failed], constraints: "set once the state is done, failed or skipped"}
      - {name: piece_count, type: whole number, required: true, min: 1}
      - {name: step, type: text, required: false}
      - {name: bytes_done, type: whole number, required: false, min: 0}
      - {name: bytes_total, type: whole number, required: false, min: 0}
      - {name: error_code, type: text, required: false}
      - {name: error_message, type: text, required: false, constraints: "never holds a secret (BR1.12)"}
      - {name: retryable, type: boolean, required: false}
      - {name: created_at, type: UTC time, required: true}
      - {name: last_activity_at, type: UTC time, required: true}
      - {name: ended_at, type: UTC time, required: false}
    relationships:
      - {to: ReceivedPiece, cardinality: "0..*", direction: owns}
      - {to: ModelLock, cardinality: "0..1", direction: holds}
  - name: ReceivedPiece
    description: One piece of the bundle that has arrived and been checked. The bytes are working storage on disk; this row says what is there.
    attributes:
      - {name: import_id, type: text, required: true}
      - {name: index, type: whole number, required: true, min: 1, max: 999999}
      - {name: sha256, type: text, required: true}
      - {name: size_bytes, type: whole number, required: true, min: 0}
      - {name: consumed, type: boolean, required: true, default: false, constraints: "true once unpacked and deleted from disk (BR1.6)"}
    constraints:
      - "unique on (import_id, index)"
  - name: ModelLock
    description: The lock that lets only one import of a model run at a time.
    attributes:
      - {name: model_key, type: text, required: true, unique: true, constraints: "the model id in lower case"}
      - {name: import_id, type: text, required: true}
      - {name: acquired_at, type: UTC time, required: true}
  - name: TrustedKey
    description: A public key whose signatures the service accepts on bundles.
    attributes:
      - {name: fingerprint, type: text, required: true, unique: true, constraints: "in the existing tool's format, groups of four hexadecimal characters"}
      - {name: key_id, type: text, required: true, unique: true}
      - {name: public_key, type: text, required: true}
      - {name: label, type: text, required: true, min: 1, max: 80}
      - {name: added_by_id, type: text, required: true}
      - {name: added_by_name, type: text, required: true}
      - {name: added_at, type: UTC time, required: true}
      - {name: revoked_at, type: UTC time, required: false}
      - {name: revoked_by_name, type: text, required: false}
  - name: RetentionSetting
    description: The one setting for how long a version is kept before an administrator is asked.
    attributes:
      - {name: retention_days, type: whole number, required: true, default: 365, min: 1, max: 3650}
      - {name: changed_by_name, type: text, required: false}
      - {name: changed_at, type: UTC time, required: false}
  - name: RetentionDecision
    description: One administrator decision about one version. It is part of the trail and is never changed afterwards except for its outcome.
    attributes:
      - {name: decision_id, type: text, required: true, unique: true}
      - {name: model_id, type: text, required: true}
      - {name: commit, type: text, required: true}
      - {name: decision, type: text, required: true, allowed: [keep, remove]}
      - {name: decided_by_id, type: text, required: true}
      - {name: decided_by_name, type: text, required: true}
      - {name: decided_at, type: UTC time, required: true}
      - {name: outcome, type: text, required: true, allowed: [done, failed, files_deleted_not_marked], constraints: "a keep is done at once; a remove is done only after both Artifactory and the Catalog agree (BR1.17)"}
      - {name: failure_code, type: text, required: false}
      - {name: failure_message, type: text, required: false, constraints: "never holds a secret"}
  - name: ArtifactoryVersionListing
    description: What the gateway learned by listing one version in Artifactory. Held in memory for one import or removal; not stored.
    attributes:
      - {name: present, type: boolean, required: true}
      - {name: files, type: list of file, required: true, constraints: "path, size, SHA-256 as Artifactory reports them"}
      - {name: locations, type: list of text, required: true, constraints: "the storage paths found by listing, never built (BR1.20)"}
```

## Summary

Seven entities. `ImportJob` with its `ReceivedPiece`s and the `ModelLock` carry the import (ADR-008). `TrustedKey` is the list of signing keys (FR1.14). `RetentionSetting` and `RetentionDecision` carry retention (FR5). `ArtifactoryVersionListing` is a short-lived value, not stored.
