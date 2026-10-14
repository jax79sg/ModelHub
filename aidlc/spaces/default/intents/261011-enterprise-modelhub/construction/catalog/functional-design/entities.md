# Entities: catalog

Inputs: `unit-of-work.md` (U2), `components.md` (Catalog, entities Model, ModelVersion, VersionFile, StoredDocument, ImportRecord, PersonalToken), `requirements.md` (FR2 to FR2.8, FR3.4, FR3.5, FR4.4, FR4.5, NFR2, NFR7), contracts C2 and C3, and the answers in `functional-design-questions.md` (written FDQ). These are logical entities of the Catalog's database, which only the Catalog reads and writes (ADR-002). "Null" below means a value that was not given, kept distinct from zero and from empty text (FR2.4).

```yaml
unit: catalog
entities:
  - name: Model
    description: One Hugging Face model, identified by its id (for example "org/name").
    attributes:
      - {name: model_id, type: text, required: true, unique: true, constraints: "unique ignoring upper and lower case; kept as first imported (BR1.10)"}
      - {name: first_imported_at, type: UTC time, required: true}
    relationships:
      - {to: ModelVersion, cardinality: "1..*", direction: owns}
      - {to: ModelSummary, cardinality: "1..1", direction: owns}
  - name: ModelVersion
    description: One commit of a model that has been imported, with the card fields and counts as they were at capture.
    attributes:
      - {name: commit, type: text, required: true, constraints: "40 hexadecimal characters; unique within the model"}
      - {name: state, type: text, required: true, allowed: [imported, removed], default: imported}
      - {name: captured_at, type: UTC time, required: true}
      - {name: license, type: text, required: false, constraints: "null when none given (BR1.5)"}
      - {name: language, type: list of text, required: false}
      - {name: tags, type: list of text, required: false}
      - {name: task, type: text, required: false}
      - {name: library, type: text, required: false}
      - {name: parameter_count, type: whole number, required: false, min: 0, constraints: "null when unknown"}
      - {name: downloads, type: whole number, required: false, min: 0, constraints: "null when not given; never 0 by default (BR1.3)"}
      - {name: likes, type: whole number, required: false, min: 0, constraints: "null when not given"}
      - {name: size_bytes, type: whole number, required: false, min: 0}
      - {name: counts_captured_at, type: UTC time, required: false}
      - {name: created_at, type: UTC time, required: false}
      - {name: last_modified_at, type: UTC time, required: false}
      - {name: has_readme, type: boolean, required: true, constraints: "false for a model with no README (BR1.6)"}
      - {name: card_text, type: text, required: false, constraints: "the README text used for search, taken from the README document when storing; cleared at removal (BR1.12)"}
      - {name: record_checksum, type: text, required: true, constraints: "SHA-256 of the canonical record and document checksums (BR1.2)"}
      - {name: record_format, type: whole number, required: true, min: 1, constraints: "version of the record format that produced the checksum"}
      - {name: removed_at, type: UTC time, required: false, constraints: "set exactly when state is removed"}
      - {name: removed_by, type: text, required: false, constraints: "who decided the removal"}
    constraints:
      - "unique on (model_id, commit)"
      - "removed_at and removed_by are both set or both empty (BR1.12)"
    relationships:
      - {to: VersionFile, cardinality: "0..*", direction: owns}
      - {to: StoredDocument, cardinality: "0..*", direction: owns}
      - {to: ImportRecord, cardinality: "1..*", direction: has}
      - {to: Ref, cardinality: "0..*", direction: points-from}
  - name: VersionFile
    description: One file listed in a version.
    attributes:
      - {name: path, type: text, required: true, constraints: "unique within the version; relative; no '..'"}
      - {name: size_bytes, type: whole number, required: true, min: 0}
      - {name: sha256, type: text, required: false, constraints: "64 hexadecimal characters; null for a listed file never downloaded (BR1.6)"}
      - {name: file_type, type: text, required: false}
      - {name: safety_scan, type: text, required: false, constraints: "Hugging Face's result as given; null when not scanned"}
      - {name: downloaded, type: boolean, required: true, constraints: "false for a file listed but never downloaded (BR1.6)"}
  - name: Ref
    description: A branch or tag name of the model pointing at a commit, as captured.
    attributes:
      - {name: name, type: text, required: true, constraints: "unique within (model, kind)"}
      - {name: kind, type: text, required: true, allowed: [branch, tag]}
      - {name: commit, type: text, required: true}
  - name: StoredDocument
    description: One document kept with a version; the content is held in the database.
    attributes:
      - {name: kind, type: text, required: true, allowed: [readme, readme_local, picture, response, manifest, bundle_description, bundle_signature, licence]}
      - {name: name, type: text, required: true, constraints: "unique within (version, kind); safe name, no '..' or slash at the start (BR1.4)"}
      - {name: content_type, type: text, required: true}
      - {name: size_bytes, type: whole number, required: true, min: 0, max: 16777216, constraints: "16 MiB per document (assumption); BR1.4"}
      - {name: sha256, type: text, required: true}
      - {name: content, type: bytes, required: true, constraints: "deleted when the version is removed, row kept (BR1.12)"}
      - {name: picture_status, type: text, required: false, allowed: [stored, unfetched], constraints: "for README pictures that could not be fetched (BR1.6)"}
  - name: ImportRecord
    description: One row of the import trail. Append-only.
    attributes:
      - {name: record_id, type: text, required: true, unique: true}
      - {name: model_id, type: text, required: true}
      - {name: commit, type: text, required: true}
      - {name: imported_by_id, type: text, required: true, constraints: "the person's Keycloak id (the token's owner)"}
      - {name: imported_by_name, type: text, required: true}
      - {name: imported_at, type: UTC time, required: true}
      - {name: computer, type: text, required: true}
      - {name: bundle_name, type: text, required: true}
      - {name: bundle_sha256, type: text, required: true}
      - {name: signing_key_fingerprint, type: text, required: true}
      - {name: tool_version, type: text, required: true}
      - {name: check_results, type: structured text, required: true, constraints: "the results of the checks made before the upload (FR2.3)"}
      - {name: outcome, type: text, required: true, allowed: [imported, repaired, skipped], constraints: "BR1.13"}
    constraints:
      - "no update and no delete (BR1.13)"
  - name: ModelSummary
    description: The one-row view of a model that the models list reads, so the list never touches documents (NFR2).
    attributes:
      - {name: model_id, type: text, required: true, unique: true}
      - {name: latest_commit, type: text, required: true, constraints: "the imported version with the latest import time (BR1.7)"}
      - {name: state, type: text, required: true, allowed: [imported, removed], constraints: "removed only when no imported version remains"}
      - {name: task, type: text, required: false}
      - {name: library, type: text, required: false}
      - {name: license, type: text, required: false}
      - {name: language, type: list of text, required: false}
      - {name: parameter_count, type: whole number, required: false}
      - {name: downloads, type: whole number, required: false}
      - {name: likes, type: whole number, required: false}
      - {name: last_modified_at, type: UTC time, required: false}
      - {name: created_at, type: UTC time, required: false}
      - {name: imported_at, type: UTC time, required: true}
      - {name: imported_by_name, type: text, required: true}
      - {name: imported_by_id, type: text, required: true}
      - {name: tags, type: list of text, required: false}
      - {name: search_text, type: text search value, required: false, constraints: "built from card_text; cleared with it (BR1.9)"}
  - name: PersonalToken
    description: A token a signed-in person made for the CLI. The value is never stored.
    attributes:
      - {name: token_id, type: text, required: true, unique: true}
      - {name: owner_id, type: text, required: true}
      - {name: owner_name, type: text, required: true}
      - {name: name, type: text, required: true, min: 1, max: 60}
      - {name: prefix, type: text, required: true, constraints: "the first 8 characters of the value, shown in lists"}
      - {name: value_hash, type: text, required: true, unique: true, constraints: "HMAC-SHA-256 with the pepper (BR1.15)"}
      - {name: scope, type: text, required: true, allowed: [import], default: import}
      - {name: created_at, type: UTC time, required: true}
      - {name: expires_at, type: UTC time, required: true}
      - {name: last_used_at, type: UTC time, required: false}
      - {name: revoked_at, type: UTC time, required: false}
      - {name: revoked_by, type: text, required: false}
  - name: CatalogSetting
    description: A setting the Catalog stores itself.
    attributes:
      - {name: key, type: text, required: true, unique: true, allowed: [token_lifetime_days]}
      - {name: value, type: whole number, required: true, min: 1, max: 365, default: 90}
      - {name: changed_by, type: text, required: false}
      - {name: changed_at, type: UTC time, required: false}
```

## Summary

Ten entities. A `Model` owns `ModelVersion`s, and each version owns its files, branch and tag refs, documents and trail rows. `ModelSummary` is the narrow row the list reads. `PersonalToken` and `CatalogSetting` support the CLI sign-in (contract C3). Documents live in the database (FDQ3 A); when a version is removed its document content is deleted but the rows and the record stay (FDQ6 B).
