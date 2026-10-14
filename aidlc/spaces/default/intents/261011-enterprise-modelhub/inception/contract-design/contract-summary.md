# Contract Summary

Inputs: `unit-of-work.md` and `unit-of-work-dependency.md` (from `inception/units-generation/`), `components.md` (from `inception/domain-design/`), `requirements.md` (from `inception/requirements-analysis/`), and your answers in `contract-design-questions.md` (written CQ). Contract numbers C1 to C8 belong to this record and are not the earlier project's C1 to C4.

No part of this system is offered to outside programs, except Artifactory's own repository address that standard tools already use. So all of C1 to C4 and C6 and C7 are inside the system, and C5 is a contract with a system we do not own.

## Contracts

| # | Provider | Consumer | Mechanism | Owner |
|---|----------|----------|-----------|-------|
| C1 | `artifactory-service` (U4), the Import API | `import-cli` (U6) | HTTP with JSON, OpenAPI `/v1`; bundle pieces sent one request each; a job the CLI starts and polls | U4 |
| C2 | `catalog` (U2), the Catalog API | `artifactory-service` (U4) and `portal` (U5) | HTTP with JSON, OpenAPI `/v1` | U2 |
| C3 | `catalog` (U2), the Personal Token API | `portal` (U5) issues, lists and revokes; `artifactory-service` (U4) checks | HTTP with JSON, OpenAPI `/v1` | U2 |
| C4 | `artifactory-service` (U4), the Retention and Keys API | `portal` (U5) | HTTP with JSON, OpenAPI `/v1` | U4 |
| C5 | External: Artifactory | `artifactory-service` (U4) | `jf hf upload` and Artifactory's web interface; we write down what we rely on | U3 (the stand-in encodes it) and U4 |
| C6 | External: Keycloak (the token claims) | `common` (U1) for `catalog` (U2), `artifactory-service` (U4) and `portal` (U5) | A signed token whose claims are fixed here | U1 |
| C7 | `common` (U1), the server conventions | `catalog` (U2), `artifactory-service` (U4), `portal` (U5), `platform` (U7) | Shared schema: health check, log line, secrets location | U1 |
| C8 | Existing: the bundle format | `import-cli` (U6) and `artifactory-service` (U4) | Unchanged; the earlier project's bundle contract | The existing `bundle` command |

## C1: The Import API (artifactory-service, for the CLI)

How a verified package gets in (CQ2 A: the bundle's pieces; CQ3 A: start it and ask). The sequence: the CLI creates an import (sending the signed description), sends each missing piece, then asks the service to start, then asks for progress until it ends. A model already fully imported is answered at the first step with "skipped", so no piece is sent. Every step can be repeated safely.

```yaml
openapi: 3.0.3
info:
  title: modelhub Import API
  version: "1"
servers:
  - url: /v1
security:
  - personalToken: []        # scope "import" only (see C3)
paths:
  /imports:
    post:
      summary: Create an import for one model version, or learn it is already imported or already in progress
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [modelId, commit, bundleName, bundleDescription, bundleSignature, computer, toolVersion]
              properties:
                modelId: {type: string, description: "organisation/name as Hugging Face writes it"}
                commit: {type: string, description: "full commit hash"}
                bundleName: {type: string}
                bundleDescription: {type: string, description: "the .bundle.json file, verbatim"}
                bundleSignature: {type: string, description: "the .bundle.sig file, verbatim"}
                computer: {type: string, description: "host name of the import computer"}
                toolVersion: {type: string}
                checkResults: {type: object, description: "the CLI's own verification result"}
      responses:
        "201": {description: "Created. Body: importId, state 'receiving', pieceCount, missingPieces", content: {application/json: {schema: {$ref: "#/components/schemas/Import"}}}}
        "200": {description: "Same model and commit already fully imported: outcome 'skipped'. No pieces are needed.", content: {application/json: {schema: {$ref: "#/components/schemas/Import"}}}}
        "409": {description: "Another import of this model is running: code 'model_locked'", content: {application/json: {schema: {$ref: "#/components/schemas/Error"}}}}
        "422": {description: "Refused before any piece is sent: 'untrusted_signing_key', 'bad_signature', 'name_rule_broken'", content: {application/json: {schema: {$ref: "#/components/schemas/Error"}}}}
  /imports/{importId}:
    get:
      summary: Progress and result
      responses:
        "200": {content: {application/json: {schema: {$ref: "#/components/schemas/Import"}}}}
        "404": {content: {application/json: {schema: {$ref: "#/components/schemas/Error"}}}}
    delete:
      summary: Cancel an import that has not finished; received pieces are removed
      responses:
        "204": {description: "Cancelled, or already gone"}
  /imports/{importId}/pieces/{index}:
    put:
      summary: Send one piece (body is the raw bytes)
      parameters:
        - {name: index, in: path, required: true, schema: {type: integer, minimum: 1, maximum: 999999}}
        - {name: X-Piece-SHA256, in: header, required: true, schema: {type: string, description: "lowercase hex checksum of this piece"}}
      responses:
        "204": {description: "Stored, or already stored with the same checksum"}
        "409": {description: "Checksum does not match the signed description: code 'piece_mismatch'; the piece is discarded", content: {application/json: {schema: {$ref: "#/components/schemas/Error"}}}}
        "413": {description: "Piece larger than the description allows: code 'piece_too_large'"}
  /imports/{importId}/start:
    post:
      summary: Start the import once every piece is present (joins, unpacks, re-verifies, uploads, records)
      responses:
        "202": {description: "Started or already running", content: {application/json: {schema: {$ref: "#/components/schemas/Import"}}}}
        "409": {description: "Pieces are still missing: code 'pieces_missing'", content: {application/json: {schema: {$ref: "#/components/schemas/Error"}}}}
components:
  securitySchemes:
    personalToken: {type: http, scheme: bearer}
  schemas:
    Import:
      type: object
      required: [importId, state]
      properties:
        importId: {type: string}
        state: {type: string, enum: [receiving, ready, verifying, uploading, recording, done, failed, cancelled, skipped]}
        outcome: {type: string, enum: [imported, completed, skipped, failed], description: "present once state is done, failed or skipped"}
        pieceCount: {type: integer}
        missingPieces: {type: array, items: {type: integer}}
        progress:
          type: object
          properties:
            step: {type: string}
            bytesDone: {type: integer}
            bytesTotal: {type: integer}
            updatedAt: {type: string, format: date-time}
        message: {type: string, description: "human-readable, never contains a secret"}
        error: {$ref: "#/components/schemas/Error"}
    Error:
      type: object
      required: [code, message, retryable]
      properties:
        code: {type: string}
        message: {type: string}
        retryable: {type: boolean}
```

Rules.

- Re-run safety: creating an import for a model and commit that has an unfinished import returns that import with its `missingPieces`; sending a piece that is already stored is accepted again; `start` on a running import returns its state.
- The service checks the signed description and every piece against it as pieces arrive, joins and unpacks them in order while removing each piece it has consumed (so disk use is about the model's size, not twice), then checks every file against the signed manifest (FR1.14).
- A model is locked per model id from creation until the import ends or is cancelled (FR1.12). An import with no activity for 24 hours is cancelled by the service (a default; see open questions).

## C2: The Catalog API (catalog, for the import service and the portal)

The only way to reach model information and the import trail (decision 2 of Domain Design). Callers: the portal carries the person's Keycloak token; the import service carries its own service token (Keycloak client credentials) and states in the body who imported on whose behalf.

```yaml
openapi: 3.0.3
info:
  title: modelhub Catalog API
  version: "1"
servers:
  - url: /v1
security:
  - keycloak: []
paths:
  /models:
    get:
      summary: The models list. Never reads stored documents (NFR2)
      parameters:
        - {name: task, in: query, schema: {type: string}}
        - {name: library, in: query, schema: {type: string}}
        - {name: license, in: query, schema: {type: string}}
        - {name: language, in: query, schema: {type: string}}
        - {name: parameters, in: query, schema: {type: string, enum: [lt1b, 6b, 12b, 32b, 128b, gt500b]}}
        - {name: importedBy, in: query, schema: {type: string}}
        - {name: importedFrom, in: query, schema: {type: string, format: date-time}}
        - {name: importedTo, in: query, schema: {type: string, format: date-time}}
        - {name: q, in: query, schema: {type: string}, description: "search the model card text and tags"}
        - {name: sort, in: query, schema: {type: string, enum: [downloads, likes, lastModified, createdAt, name, importedAt]}}
        - {name: page, in: query, schema: {type: integer, minimum: 1, default: 1}}
        - {name: pageSize, in: query, schema: {type: integer, default: 30, maximum: 100}}
      responses:
        "200": {description: "items (summary of each model's latest version), total, facets (counts per filter value)"}
  /models/{modelId}:
    get:
      summary: One model with its versions and branches and tags
      responses:
        "200": {description: "the model, its versions (state imported or removed), and refs"}
        "404": {description: "not found: code 'not_found'"}
  /models/{modelId}/versions/{commit}:
    get:
      summary: Full record of one version (card fields, counts, files, history pointers; documents listed, not included)
      responses:
        "200": {description: "version record; empty values are null, never 0 or empty text"}
        "404": {description: "not found: code 'not_found'"}
    put:
      summary: Record a version, its files, its documents and its import-trail row in ONE transaction (service token only)
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              required: [record]
              properties:
                record: {type: string, description: "JSON: version, files[], importRecord{importedBy, importedAt, computer, bundleName, bundleSha256, signingKeyFingerprint, toolVersion, checkResults, outcome}"}
                documents: {type: array, items: {type: string, format: binary}, description: "readme, pictures, raw responses, manifest, bundle description and signature, licence file; each named by kind/name"}
      responses:
        "201": {description: "recorded"}
        "200": {description: "already recorded identically: nothing changed (repeat is safe)"}
        "409": {description: "a different record already exists for this model and commit: code 'record_conflict'"}
        "422": {description: "invalid record: code 'invalid_record'"}
  /models/{modelId}/versions/{commit}/documents/{kind}/{name}:
    get:
      summary: One stored document (README, picture, saved response, ...), served as data, never rendered
      responses:
        "200": {description: "bytes with the stored content type"}
        "404": {description: "not found: code 'not_found'"}
  /models/{modelId}/versions/{commit}/removal:
    post:
      summary: Mark a version removed (service token only; used by Retention after Artifactory deleted the files)
      responses:
        "200": {description: "marked removed; its trail rows stay"}
        "409": {description: "already removed or not found"}
  /versions:
    get:
      summary: Versions by age, for Retention (service token only)
      parameters:
        - {name: state, in: query, schema: {type: string, enum: [imported, removed]}}
        - {name: importedBefore, in: query, schema: {type: string, format: date-time}}
        - {name: page, in: query, schema: {type: integer}}
      responses:
        "200": {description: "versionKey, modelId, commit, importedAt, importedBy, sizeBytes"}
  /trail:
    get:
      summary: The import trail (import records), filterable by model and by person
      responses:
        "200": {description: "records newest first; the portal merges retention decisions from C4 into the same view"}
components:
  securitySchemes:
    keycloak: {type: http, scheme: bearer, bearerFormat: JWT}
```

Rules.

- A repeat of the same `PUT` with the same content changes nothing and answers 200; a different record for the same model and commit is refused, never overwritten (FR1.4, FR1.8).
- The record, its files, its documents and its trail row are stored together or not at all (FR2.5).
- Fields the importer does not know stay in the saved responses (FR2.6). Consumers ignore fields they do not know.
- The list endpoint answers in under 1 second for 1,000 models (NFR2); this is a contract promise the Catalog's design must meet.

## C3: The Personal Token API (catalog)

A signed-in person makes a personal token in the portal and pastes it into the CLI (CQ4 C). The system issues and checks its own tokens (CQ7 B). Safeguards, all defaults to confirm (see assumptions): the token works for importing only; it expires after a set time (default 90 days, an administrator can change it); it is shown once; only its hash is stored; the person or an administrator can revoke it at once.

```yaml
openapi: 3.0.3
info:
  title: modelhub Personal Token API
  version: "1"
servers:
  - url: /v1
paths:
  /tokens:
    post:
      summary: Make a personal token for the signed-in person (Keycloak token required; the portal calls this)
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                name: {type: string, description: "a label the person chooses, e.g. 'import laptop'"}
      responses:
        "201":
          description: "The token value is returned ONCE and never again."
          content:
            application/json:
              schema:
                type: object
                properties:
                  tokenId: {type: string}
                  token: {type: string, description: "shown once; 256 random bits, text-encoded, with a recognisable prefix"}
                  scope: {type: string, enum: [import]}
                  expiresAt: {type: string, format: date-time}
    get:
      summary: The signed-in person's own tokens (never the value): id, name, prefix, createdAt, expiresAt, lastUsedAt, revokedAt
      responses:
        "200": {description: "list"}
  /tokens/{tokenId}:
    delete:
      summary: Revoke at once (the owner, or an administrator for any token)
      responses:
        "204": {description: "revoked or already revoked"}
  /tokens/introspect:
    post:
      summary: Is this token valid, and whose is it? (service token only; used by the import service)
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [token]
              properties:
                token: {type: string}
      responses:
        "200":
          content:
            application/json:
              schema:
                type: object
                required: [active]
                properties:
                  active: {type: boolean}
                  person: {type: string, description: "the Keycloak subject and user name of the owner when the token was made"}
                  scope: {type: string}
                  expiresAt: {type: string, format: date-time}
```

Rules.

- A token that is expired, revoked, unknown or used outside its scope is answered `active: false` with no reason given to the caller; the import service answers the CLI with status 401 and the code `token_invalid`.
- The CLI keeps the token in a file only that person can read and never prints it (FR1.11).
- Every use updates `lastUsedAt`. The value of a token never appears in a log, in the trail or in an error message.

## C4: The Retention and Keys API (artifactory-service, for the portal)

Administrator-only (the `modelhub-admin` role, C6) except where noted. The portal passes the signed-in person's Keycloak token.

```yaml
openapi: 3.0.3
info:
  title: modelhub Retention and Keys API
  version: "1"
servers:
  - url: /v1
security:
  - keycloak: []
paths:
  /retention/settings:
    get:
      summary: The retention period (any signed-in person)
      responses:
        "200": {description: "periodDays, changedBy, changedAt"}
    put:
      summary: Change the retention period (administrator)
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [periodDays]
              properties:
                periodDays: {type: integer, minimum: 1}
      responses:
        "200": {description: "changed"}
        "403": {description: "not an administrator: code 'forbidden'"}
  /retention/due:
    get:
      summary: Versions older than the period, counted from import time (administrator)
      responses:
        "200": {description: "list of versions with importedAt, importedBy, ageDays"}
  /retention/decisions:
    get:
      summary: Past keep-or-remove decisions (any signed-in person; the portal merges them into the trail)
      responses:
        "200": {description: "decisionId, modelId, commit, decision, decidedBy, decidedAt, outcome"}
    post:
      summary: Decide keep or remove for one version (administrator)
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [modelId, commit, decision]
              properties:
                modelId: {type: string}
                commit: {type: string}
                decision: {type: string, enum: [keep, remove]}
      responses:
        "200": {description: "outcome: kept, removed, or removal_failed (nothing marked removed)"}
        "403": {description: "not an administrator: code 'forbidden'"}
        "409": {description: "version not due or already removed"}
  /trusted-keys:
    get:
      summary: The import service's trusted signing keys (administrator)
      responses:
        "200": {description: "keyId, fingerprint, name, addedBy, addedAt, status"}
    post:
      summary: Add a trusted key (administrator). The fingerprint must be typed as well as the key file sent
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [publicKey, typedFingerprint, name]
              properties:
                publicKey: {type: string, description: "the public key file, verbatim"}
                typedFingerprint: {type: string}
                name: {type: string}
      responses:
        "201": {description: "added"}
        "422": {description: "fingerprint does not match the key: code 'fingerprint_mismatch'"}
  /trusted-keys/{keyId}:
    delete:
      summary: Stop trusting a key (administrator); bundles already imported stay
      responses:
        "204": {description: "removed or already removed"}
```

## C5: What We Rely On Artifactory To Do (external)

Artifactory is not ours. This is the list of behaviours the system depends on. It is the starting point for the stand-in and must be confirmed on a real Artifactory; you agreed at intent capture that JFrog's documentation is only a starting point (IQ23 B). Everything is taken from JFrog's documentation unless marked "not documented".

```yaml shared-schema
contract: C5-artifactory-reliance
status: "documented by JFrog; NOT tested against a real instance"
repository:
  type: "local Hugging Face repository, Machine Learning layout"
  address: "https://<platform>/artifactory/api/huggingfaceml/<repo-key>"
  auth: "bearer token of a service account (identity token)"
upload:
  how: "jf hf upload <folder> <model-id>   (wraps huggingface_hub upload_folder)"
  revision: "the full commit hash"
  client: "huggingface_hub up to 1.19.0 (Xet transfers up to 1.18.0)"
  overwrite: "a repeat of the same revision overwrites unless Delete/Overwrite permission is off, then 409. The importer never asks to overwrite and treats 409 as failed"
  large_files: "Git LFS, or Xet when enabled"
names:
  organisation: "letters, numbers, single hyphens; not starting or ending with a hyphen; not all digits"
  model: "letters, numbers, hyphen, underscore, period"
  revision: "letters, numbers, hyphen, period"
other_calls_needed:
  - "list the files of a version and read their checksums"
  - "delete a version's files"
  - note: "the path where the Machine Learning layout stores files is NOT documented on the pages read. The gateway must discover paths by listing, never build them"
unsupported:
  - "Hugging Face Spaces"
  - "the other native huggingface-cli commands"
to_confirm_on_a_real_instance:
  - "the version of Artifactory and that a local Hugging Face repository can be created"
  - "the 409 answer on overwrite, and its exact body"
  - "how a version's files are listed and deleted in the Machine Learning layout"
  - "how names that break the rules are refused"
```

## C6: The Keycloak Token Claims (external)

What `common` (U1) requires of a Keycloak token, so all three server-side units check tokens the same way (CQ5 A).

```yaml shared-schema
contract: C6-keycloak-token
checked_by: "common (U1), used by catalog, artifactory-service and portal"
format: "JWT signed with the realm's key, fetched from Keycloak's published key address when the service starts and refreshed when an unknown key id appears"
required_claims:
  iss: "the realm address"
  aud: "includes the client id 'modelhub'"
  exp: "not past, allowing 60 seconds of clock difference"
  sub: "the person's stable id"
  preferred_username: "shown in the trail"
admin:
  rule: "realm_access.roles contains 'modelhub-admin'"
  who_assigns: "the Keycloak administrators"
service_callers:
  - "artifactory-service calls catalog with a token obtained through Keycloak client credentials; its client id is 'modelhub-artifactory-service'"
  - "portal calls catalog and artifactory-service with the signed-in person's token"
failure:
  - "missing, malformed, expired or wrong-audience token: HTTP 401, code 'token_invalid', no detail"
  - "valid token without the role for the action: HTTP 403, code 'forbidden'"
secrets:
  - "client secrets are read from the server's secret files (C7), never from configuration or logs"
```

## C7: Server Conventions (common)

What every server-side unit offers the server, so the platform can run and watch them alike.

```yaml shared-schema
contract: C7-server-conventions
health:
  live: "GET /healthz -> 200 {status: ok}   (the process is up)"
  ready: "GET /readyz -> 200 {status: ok|degraded, checks: {database: ok|down, keycloak: ok|down, artifactory: ok|down}}  or 503 when it cannot serve"
  no_secrets: true
logging:
  destination: "standard output, one JSON object per line"
  fields: "ts (UTC, ISO 8601), level, service, event, requestId, person (user name only), message"
  never_logged: ["tokens", "passwords", "secret file contents", "personal-token values"]
secrets:
  location: "files under /run/secrets/ (or the folder named by MODELHUB_SECRETS_DIR), one file per secret, readable only by the service"
  names: ["database_password", "keycloak_client_secret", "artifactory_token", "token_hash_pepper"]
configuration:
  source: "environment variables for non-secret values; a documented name per value"
timeouts_default_seconds: {connect: 5, read: 30, piece_upload: 600}
```

## C8: The Bundle Format (existing, unchanged)

The earlier project's bundle contract is kept as it is: an uncompressed standard archive of a model's download folder, cut into plain pieces named `<model>--<commit12>.part-<index>`, with `<stem>.bundle.json` (piece list, checksums, sizes, model and commit) and `<stem>.bundle.sig` (an Ed25519 signature). `import-cli` sends exactly these files (C1); `artifactory-service` re-verifies them with the same code (decision 5 of Domain Design). The old project's contract summary (`261009-hf-airgap-cli/inception/contract-design/contract-summary.md`, contracts C1 to C3) is the authority for the details.

## Errors, Timeouts And Retries At Each Boundary

| Boundary | Timeout | Retry | A repeat is safe because |
|----------|---------|-------|---------------------------|
| C1 create, status, start | 30 s | 5 retries, waits 1, 2, 4, 8, 16 s with small random extra | Creating returns the existing import; start on a running import returns its state |
| C1 piece upload | 10 min per piece | same waits | A stored piece with the same checksum is accepted again |
| C1 polling | 30 s per poll, every 5 s while running | keeps polling; gives up only if the service is unreachable for 5 minutes, then tells the person to run again | The import continues on the server without the CLI |
| C2 from the import service | 30 s (documents up to 10 min) | 5 retries with the same waits on 503 and network errors only | `PUT` of the same content answers 200 |
| C2 from the portal | 30 s | none automatic; the portal says plainly that the Catalog is unreachable (FR3.8) | reads only |
| C3 introspect | 5 s | 2 retries; if still failing, the import answer is 503 `catalog_unavailable` | read only |
| C4 | 30 s | none automatic for decisions (a person repeats on purpose) | a repeated keep or remove on a decided version answers 409 |
| C5 upload | no limit while data flows, 10 min with no progress | 5 retries with the same waits, then the model is failed | A repeat after a partial upload finds the version either complete or absent; an existing version is never overwritten |

Error body (C1 to C4): `{code, message, retryable}`. A `retryable: true` error is one the caller may repeat after waiting. No message ever carries a secret.

## Versioning And Ownership Rules

- **Version in every address** (`/v1/...`) (CQ6 A). A breaking change gets `/v2/...` and the old version is served for one release. Adding a field or an endpoint is not breaking; consumers ignore fields they do not know.
- **A CLI that is too old** gets HTTP 426 with `minimumCliVersion`, and tells the person to update. A CLI newer than the server gets a clear 404 on any path it does not know.
- **Owner of each spec** is the provider unit (table above). A change to a spec is made by its owner, agreed with the consumers, recorded as a decision, and the stand-in and the tests are updated in the same change.
- **Single place for names and rules**: Artifactory's naming rules live in the Artifactory gateway only (decision 4 of Domain Design); no contract repeats them except to say where they are checked.

## Effects On Approved Documents

CQ7 B (the system issues its own personal tokens) and CQ4 C (personal tokens for the CLI) add things the earlier stages did not have. These are applied in the documents, tagged with the decision, so you can see them at this stage's approval.

| Document | What changes |
|----------|--------------|
| `requirements.md` FR1.2 | The CLI uses a personal token made in the portal, not a Keycloak sign-in typed in the CLI |
| `requirements.md` new FR4.4 to FR4.6 | Making, listing and revoking personal tokens in the portal; token safeguards (import only, expiry, shown once, hash only) |
| `requirements.md` open questions and A6 | The browserless sign-in question is answered; A6 is replaced |
| `components.md` | The Catalog also owns the PersonalToken entity and issues, lists, revokes and checks tokens; SignIn becomes a token-reading helper in the CLI |
| `decisions.md` | New ADR-010 for the system-issued personal token |
| Unit documents (`unit-of-work.md`, `unit-of-work-story-map.md`, traceability files) | U2 and U5 carry the token work; FR4.4 to FR4.6 are mapped |

## Open Questions

| Contract | Question | Blocks |
|----------|----------|--------|
| C5 | How are a version's files listed and deleted in the Machine Learning layout, and what are the exact paths? Not in the pages read; the gateway must discover paths | U4, U3 |
| C5 | What does Artifactory answer on overwrite, and does it also refuse a name-rule break in a readable way? | U4, U3 |
| C1 | How long may an import with no activity wait before it is cancelled (24 hours is a default here)? | U4 |
| C3 | What are the token defaults the owner wants: lifetime (90 days here), import-only scope, how many tokens a person may hold? | U2, U5 |
| C6 | Is the Keycloak client id `modelhub` and the service client id `modelhub-artifactory-service` acceptable to the Keycloak administrators? | U1, U4 |
| C6 | How are signing keys published for the token check when Keycloak is behind a proxy? | U1 |
| C7 | Does the central logging expect a particular log field naming? | U1, U7 |
