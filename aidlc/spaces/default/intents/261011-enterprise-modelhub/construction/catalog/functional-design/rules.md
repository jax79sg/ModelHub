# Rules: catalog

The decisions the Catalog makes. Sources are requirement, contract and decision IDs and the answers in `functional-design-questions.md` (FDQ).

```yaml
unit: catalog
rules:
  - id: BR1.1
    statement: A version, its files, refs, documents, summary row, search text and trail row are stored together in one transaction, or not at all.
    category: constraint
    applies_to: [ModelVersion, VersionFile, StoredDocument, ImportRecord, ModelSummary]
    trigger: PUT of a version record
    logic: "Do every write for the call inside one database transaction. IF any step fails (including a document that cannot be stored) THEN roll back everything and answer 500 with code store_failed, leaving no version row, file row, document, summary change or trail row. Success answers 201."
    violation: roll back; 500 store_failed
    source: [FR2.5, AC2.1, NFR4]
  - id: BR1.2
    statement: A repeat of an identical record changes nothing, and a different record for the same model and commit is refused, never overwritten; the one exception is a removed version, which a new record brings back.
    category: constraint
    applies_to: [ModelVersion]
    trigger: PUT of a version record
    logic: "Compute record_checksum as the SHA-256 of the canonical form of the record (its fields and file list, the import fields without imported_at) plus each document's kind, name and SHA-256, sorted. IF a version for (model, commit) exists AND its record_checksum is equal THEN answer 200 and change nothing, adding no trail row. IF it exists with a different checksum THEN answer 409 record_conflict and change nothing. record_format is stored with the checksum, and a checksum made under another format is never compared as equal. EXCEPTION (added after artifactory-service FDQ3 B): IF the existing version is in state removed THEN a valid PUT is accepted as a reinstatement and the checks above do not apply: in one transaction set state imported, clear removed_at and removed_by, replace the record fields, files, refs and documents with the new ones, store the new record_checksum, add one trail row, and update the summary (BR1.7). Answer 201."
    violation: 409 record_conflict
    source: [FR1.4, FR1.8, C2 rules, FDQ4 A]
  - id: BR1.3
    statement: A value that was not given is stored as empty (null); the Catalog never turns it into 0 or empty text.
    category: validation
    applies_to: [ModelVersion, VersionFile]
    trigger: PUT of a version record; any read
    logic: "A field that is absent, null, or empty text where a number or an optional text is expected is stored as null. A number is stored exactly as given, including 0. Reads return null as null."
    violation: not applicable
    source: [FR2.4, AC2.2]
  - id: BR1.4
    statement: A record that lacks a required field, or has a malformed value, is refused with 422 and nothing is stored.
    category: validation
    applies_to: [ModelVersion, VersionFile, StoredDocument, ImportRecord]
    trigger: PUT of a version record
    logic: "Refuse with 422 invalid_record naming the field IF: the model id is empty; the commit is not 40 hexadecimal characters; captured_at is not UTC; any import field (person id and name, imported_at, computer, bundle name, bundle SHA-256, signing key fingerprint, tool version, check results, outcome) is missing; a file path is empty, repeated, absolute or has '..'; a size is negative; a checksum is not hexadecimal of the right length; a document name repeats within its kind, starts with '/' or contains '..'; a document is larger than 16 MiB; or a stated document checksum differs from the content."
    violation: 422 invalid_record
    source: [FR2.1, FR2.3, C2]
  - id: BR1.5
    statement: The licence name is stored as given; a model with none is stored with an empty licence, and a licence file is stored as a document.
    category: policy
    applies_to: [ModelVersion, StoredDocument]
    trigger: PUT of a version record
    logic: "license is the given name or null. A licence file, when sent, is stored as a document of kind licence. The Catalog never invents a licence; showing 'no licence given' is the portal's job."
    violation: not applicable
    source: [FR2.7]
  - id: BR1.6
    statement: A missing README, a file listed but never downloaded, and a picture that could not be fetched are each stored as such.
    category: policy
    applies_to: [ModelVersion, VersionFile, StoredDocument]
    trigger: PUT of a version record
    logic: "has_readme is false when no readme document is sent. A file entry with downloaded false is stored with sha256 null if none was computed. A picture whose content could not be fetched is stored as a row with picture_status unfetched and empty content, never skipped."
    violation: not applicable
    source: [FR2.8]
  - id: BR1.7
    statement: Each model has one summary row, always showing its imported version with the latest import time.
    category: calculation
    applies_to: [ModelSummary]
    trigger: storing a version; marking a version removed
    logic: "After every store or removal, inside the same transaction, set the summary row from the imported version with the greatest import time (ties: the larger commit text). IF the model has no imported version left THEN keep the last values and set state removed."
    violation: not applicable
    source: [NFR2, FDQ2 A, C2]
  - id: BR1.8
    statement: The models list filters, sorts and pages from the summary rows alone, and never reads documents.
    category: policy
    applies_to: [ModelSummary]
    trigger: GET /models
    logic: "Filters (task, library, licence, language, parameter-size band, importedBy, importedFrom, importedTo) are combined with AND; a value that matches nothing returns an empty list, not an error. importedFrom and importedTo are inclusive and compare with imported_at. Sort choices: downloads, likes, lastModified, createdAt, name, importedAt; the default is downloads, largest first; the order is descending except name (ascending); null values sort last; ties break on model id. Page size defaults to 30 and is at most 100; page starts at 1. Answer the total and the counts per filter value. Removed-state models are included only when the caller asks for them."
    violation: 422 for an unknown sort or filter value, code invalid_query
    source: [FR3.4, AC3.2, NFR2, C2]
  - id: BR1.9
    statement: Text search matches whole words in the card text with English word forms, and parts of words in the model id and tags.
    category: policy
    applies_to: [ModelSummary]
    trigger: GET /models with q
    logic: "Split q into words (at most 10, each at most 100 characters; q at most 200 characters, else 422). A model matches when EVERY word matches either the card text (whole word, English word forms, so 'quantize' finds 'quantized') OR the model id or a tag (case-insensitive part of the text, at least 3 characters). Rank card-text matches by relevance first, then by downloads. Empty q is ignored. A removed version's card text is empty (BR1.12), so it matches only by id and tags."
    violation: 422 invalid_query for an over-long q
    source: [FR3.5, AC3.3, FDQ1 C]
  - id: BR1.10
    statement: Model ids are the same model regardless of upper or lower case.
    category: constraint
    applies_to: [Model]
    trigger: PUT of a version record; any lookup by model id
    logic: "Look up a model by id ignoring case. A PUT whose id differs only in case from an existing model is recorded under the existing model and the stored spelling is kept."
    violation: not applicable
    source: [FR2.1, assumption]
  - id: BR1.11
    statement: Documents are served as data and never as a page.
    category: policy
    applies_to: [StoredDocument]
    trigger: GET of a document
    logic: "Answer with the stored bytes and the stored content type, EXCEPT that html, svg, javascript and XML types are answered as application/octet-stream. Always add Content-Disposition attachment, X-Content-Type-Options nosniff and a Content-Security-Policy of 'sandbox'. A removed version's document answers 410 gone."
    violation: not applicable
    source: [FR2.2, FR3.7, C2]
  - id: BR1.12
    statement: Marking a version removed keeps the record, file list and trail and deletes the documents' content; only a new import record (BR1.2) brings it back.
    category: constraint
    applies_to: [ModelVersion, StoredDocument, ModelSummary]
    trigger: POST removal
    logic: "Only a service token may call it. IF the version is in state imported THEN, in one transaction: set state removed with removed_at and removed_by; delete every document's content (keeping its row with kind, name, size and checksum); clear card_text and the summary search_text if the summary row points at this version; update the summary per BR1.7. Answer 200. IF the version is already removed or not found THEN answer 409. Trail rows are not touched."
    violation: 409
    source: [FR5.5, FDQ6 B, C2]
  - id: BR1.13
    statement: The import trail is only ever added to.
    category: constraint
    applies_to: [ImportRecord]
    trigger: any call
    logic: "The only write to ImportRecord is the insert made by a successful first PUT of a version (BR1.1). A repeat PUT (BR1.2) adds no row. A skipped or repaired import is recorded by its own PUT of an import-only record with outcome skipped or repaired, which adds one trail row and touches nothing else. There is no call that updates or deletes a trail row. Reads return newest first and may be filtered by model and by person."
    violation: not applicable
    source: [FR2.3, ADR-007, C2]
  - id: BR1.14
    statement: Reads need a signed-in person; writes and the retention calls need the import service's own service token.
    category: authorization
    applies_to: [Model, ModelVersion, ImportRecord, PersonalToken]
    trigger: any call
    logic: "Every call needs a valid Keycloak token (common rule). The calls PUT version, POST removal, GET /versions and POST /tokens/introspect also need the service client identity modelhub-artifactory-service, else 403 forbidden. A personal import token is never accepted by the Catalog itself; the import service presents it for introspection only."
    violation: 403 forbidden
    source: [NFR5, C2, C3, C6]
  - id: BR1.15
    statement: A personal token is made for the signed-in person, shown once, and stored only as a keyed hash.
    category: policy
    applies_to: [PersonalToken]
    trigger: POST /tokens
    logic: "The caller must be a signed-in person (a Keycloak token for a person, not a service). name is 1 to 60 characters. A person may hold at most 20 tokens that are neither revoked nor expired (assumption); more is refused with 422 too_many_tokens. The value is the prefix mhi_ followed by 256 random bits encoded as text. Store value_hash as HMAC-SHA-256 of the value with the token_hash_pepper secret, prefix as the first 8 characters, scope import, and expires_at as now plus the token lifetime setting. Return the value only in this answer."
    violation: 422
    source: [FR4.4, ADR-010, FDQ5 A]
  - id: BR1.16
    statement: A token is valid only if it exists, is not revoked and has not expired; checking it tells the import service who it belongs to and nothing else.
    category: authorization
    applies_to: [PersonalToken]
    trigger: POST /tokens/introspect
    logic: "Hash the presented value as in BR1.15 and look it up. Answer active true with owner id, owner name and scope import only when found, revoked_at empty and expires_at in the future. Otherwise answer active false with the reason revoked, expired or unknown. Set last_used_at only when the stored value is older than one minute. The value and the hash are never logged."
    violation: active false
    source: [FR4.5, AC4.2, AC4.3, FDQ5 A]
  - id: BR1.17
    statement: Revoking a token takes effect at once, can be done by its owner or an administrator, and is permanent.
    category: authorization
    applies_to: [PersonalToken]
    trigger: DELETE /tokens/{tokenId}; GET /tokens
    logic: "IF the caller owns the token OR is an administrator THEN set revoked_at and revoked_by (if not already set) and answer 204, also on repeat. ELSE answer 404 (not 403, so other people's ids are not revealed). GET /tokens lists the caller's own tokens: id, name, prefix, created, expires, last used, revoked; an administrator may ask for all. A list never holds the value or the hash."
    violation: 404
    source: [FR4.5, FR4.6, AC4.3]
  - id: BR1.18
    statement: The token lifetime is a setting only an administrator can change, from 1 to 365 days, and changes apply to tokens made afterwards.
    category: policy
    applies_to: [CatalogSetting, PersonalToken]
    trigger: change of token_lifetime_days; POST /tokens
    logic: "Default 90. A value outside 1 to 365 is refused with 422. An existing token keeps the expires_at it was made with."
    violation: 422
    source: [FR4.5, A11]
  - id: BR1.19
    statement: Fields the importer sent that the Catalog does not know are kept in the saved responses and never stop the store.
    category: policy
    applies_to: [StoredDocument, ModelVersion]
    trigger: PUT of a version record
    logic: "Unknown fields in the record are ignored by the checks. The saved Hugging Face responses and the summary document are stored as received (kind response), so an unknown field survives there."
    violation: not applicable
    source: [FR2.6, C2 rules]
  - id: BR1.20
    statement: Retention can list versions by state and age, oldest first, and nothing else about them.
    category: policy
    applies_to: [ModelVersion]
    trigger: GET /versions
    logic: "Service token only (BR1.14). Filter by state and by imported_at before the given time; sort oldest import time first; page. Return version key, model id, commit, imported_at, imported_by and size only."
    violation: 403
    source: [FR5.2, C2]
  - id: BR1.21
    statement: The Catalog's database changes are versioned steps that keep existing data, applied at start-up, and the service refuses a database newer than itself.
    category: constraint
    applies_to: [Model, ModelVersion]
    trigger: service start-up
    logic: "Apply pending steps in order while holding a database lock so two copies cannot do it at once. Each step is recorded when done. IF the database holds a step the code does not know THEN refuse to start and say so. A step never removes data without being the second step of a two-release removal."
    violation: refuse to start
    source: [FR6.6, AC6.2, NFR6]
```

## Rules Summary

| ID | Rule | Category |
|----|------|----------|
| BR1.1 | One transaction per store | constraint |
| BR1.2 | Identical repeat 200; different 409 | constraint |
| BR1.3 | Unknown stays null | validation |
| BR1.4 | Malformed record 422 | validation |
| BR1.5 | Licence stored as given | policy |
| BR1.6 | Missing README, file, picture stored as such | policy |
| BR1.7 | Summary row = latest imported version | calculation |
| BR1.8 | List from summary rows only | policy |
| BR1.9 | Search rules | policy |
| BR1.10 | Model id ignores case | constraint |
| BR1.11 | Documents served as data | policy |
| BR1.12 | Removal keeps record and trail | constraint |
| BR1.13 | Trail append-only | constraint |
| BR1.14 | Who may call what | authorization |
| BR1.15 | Token made, shown once, keyed hash | policy |
| BR1.16 | Token introspection | authorization |
| BR1.17 | Revoke and list tokens | authorization |
| BR1.18 | Token lifetime setting | policy |
| BR1.19 | Unknown fields kept | policy |
| BR1.20 | Versions for retention | policy |
| BR1.21 | Database upgrade steps | constraint |
