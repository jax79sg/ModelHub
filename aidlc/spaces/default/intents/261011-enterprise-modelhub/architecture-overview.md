# Enterprise ModelHub: Architecture Overview

This page summarises the design in `aidlc/spaces/default/intents/261011-enterprise-modelhub/`. It is a design only; no code has been written for it. Requirement IDs (FR, NFR), rule IDs (BR) and contract IDs (C1 to C8) point to the detailed documents. The work was done in the AI-DLC stages: intent, feasibility, scope, requirements, domain design, units, contracts, delivery plan, then for each of seven units the functional design, quality targets, quality design and infrastructure design.

## 1. What this is

Today, a command-line program downloads public Hugging Face models online and packs them into signed bundles. On the air-gapped side it verifies and unpacks them into a folder, which a prototype web app can browse. The enterprise version does three more things:

1. The CLI imports a verified bundle into the organisation's **existing Artifactory** (Hugging Face repository, Machine Learning layout), through a server-side import service.
2. Everything *about* each model (card fields, files, README and pictures, who imported it and when, retention decisions) is stored in a **PostgreSQL database**.
3. The web app becomes a **portal** with Keycloak sign-in, reading only from the database, and hosted with the other parts as **Docker containers**.

## 2. The whole system at a glance

```mermaid
flowchart TB
    subgraph Online["Internet side (existing tools)"]
        Pull["modelhub pull / bundle"]
    end
    Drive[("Removable drive: signed split bundles")]
    Pull --> Drive

    subgraph Airgap["Air-gapped network"]
        CLI["Import computer: modelhub import"]
        Browser["People: web browser"]
        subgraph Server["One Linux server with Docker (Compose)"]
            Proxy["proxy (nginx, TLS, port 443)"]
            Portal["portal"]
            AS["artifactory-service"]
            Cat["catalog"]
            DB[("PostgreSQL: catalog and service schemas")]
            Work[("import-work volume 500 GB")]
        end
        KC["Keycloak (existing)"]
        ART[("Artifactory (existing)")]
        Mon["Central logging and monitoring (existing)"]
    end

    Drive --> CLI
    CLI -->|"HTTPS /v1/imports"| Proxy
    Browser -->|HTTPS| Proxy
    Proxy --> Portal
    Proxy --> AS
    Portal --> Cat
    Portal --> AS
    AS --> Cat
    Cat --> DB
    AS --> DB
    AS --> Work
    AS -->|"jf hf upload"| ART
    Portal -.->|sign-in| KC
    Browser -.->|"fetch models with standard tools"| ART
    Server -.->|"logs and health"| Mon
```

Text fallback: people and import computers reach only the proxy. The proxy sends web pages to the portal and import calls to `artifactory-service`. The portal calls the Catalog and `artifactory-service`; `artifactory-service` calls the Catalog and uploads to the existing Artifactory; both services use PostgreSQL; sign-in is with the existing Keycloak. Model files are fetched straight from Artifactory with standard tools and never pass through these containers.

## 3. Where each kind of information lives

| Information | Held in | Source of truth for | Why |
|---|---|---|---|
| Model files (weights, tokenizers, ...) | Artifactory | the files | Artifactory is the organisation's artifact store; the portal never serves files |
| Model information: card fields, counts, file list, refs, licence | PostgreSQL (Catalog schema) | the information | searchable and filterable in under a second |
| README, pictures, saved Hugging Face responses, manifests, bundle signatures | PostgreSQL, separate documents table | the documents | stored in the same transaction as the record |
| Import trail (who, when, which computer, which signing key) | PostgreSQL, append-only table | the trail | accountability |
| Retention decisions, trusted signing keys, import jobs, locks | PostgreSQL (artifactory-service schema) | those records | not model information (ADR-003, ADR-006) |
| Personal tokens (hash only) | PostgreSQL (Catalog schema) | CLI sign-in | shown once, stored as a keyed hash |

## 4. The seven units (what gets built)

```mermaid
flowchart LR
    common["U1 common (library)"]
    stand["U3 artifactory-stand-in (test only)"]
    cat["U2 catalog"]
    as["U4 artifactory-service"]
    portal["U5 portal"]
    cli["U6 import-cli"]
    plat["U7 platform (packaging)"]
    common --> cat
    common --> as
    common --> portal
    cat --> as
    stand --> as
    cat --> portal
    as --> portal
    as --> cli
    cat --> plat
    as --> plat
    portal --> plat
```

Arrows mean "is needed by". Each unit went through functional design, quality targets (NFR), quality design and infrastructure design.

| Unit | What it is | Delivered as |
|---|---|---|
| U1 common | Token check, secrets, JSON logging, health checks; shared by the three services | library inside the service images |
| U2 catalog | The only reader and writer of model information, trail and tokens | container |
| U3 artifactory-stand-in | An imitation of Artifactory so everything can be built and tested without one | test code only, never delivered |
| U4 artifactory-service | Import (re-check, upload, record), trusted keys, retention, the only caller of Artifactory | container (with the JFrog CLI) |
| U5 portal | The web app (from `web/`), now with sign-in, search, import trail, token page, admin screens | container |
| U6 import-cli | `modelhub import`, `login`, `logout` added to the existing program | the existing single-file program and offline packs |
| U7 platform | Compose file, proxy, secrets, volumes, server pack, upgrade and return steps | files and scripts |

## 5. How an import works

```mermaid
sequenceDiagram
    autonumber
    actor P as Person
    participant C as modelhub import (CLI)
    participant S as artifactory-service
    participant K as catalog
    participant A as Artifactory

    P->>C: modelhub import bundle
    C->>C: verify bundle (trusted key, every piece)
    C->>S: create import (signed description, signature)
    S->>K: check personal token
    S->>S: names, signature, trusted keys
    S->>A: list version, compare files with manifest
    S->>K: version state
    alt already complete in both
        S-->>C: skipped (trail row added)
    else needs work
        S-->>C: created, missing pieces
        loop each missing piece
            C->>S: send piece (checksum)
        end
        C->>S: start
        S->>S: unpack, delete pieces as used, check manifest
        opt files not in Artifactory
            S->>A: jf hf upload (never overwrite)
            S->>A: list and compare again
        end
        S->>K: record version, documents, trail row (one transaction)
        S-->>C: done (imported or completed)
    end
    C-->>P: report and exit status 0, 1 or 2
```

The service decides one of four plans from what Artifactory and the Catalog each hold (rule BR1.3 of `artifactory-service`):

```mermaid
flowchart TD
    A["Create import"] --> B{"Artifactory holds the version?"}
    B -->|"complete, matches manifest"| C{"Catalog has it imported?"}
    B -->|"nothing"| D{"Catalog has it imported?"}
    B -->|"partial or different"| X["Fail: artifactory_inconsistent, delete nothing"]
    C -->|yes| S["SKIP: report skipped, add trail row"]
    C -->|"no, or removed"| F["FINISH: record in Catalog, no upload"]
    D -->|yes| R["REPAIR: upload again, keep record"]
    D -->|"no, or removed"| U["FULL: upload and record"]
```

An import can be stopped at any moment and run again: every request is safe to repeat, pieces already stored are not sent again, and at start-up any import that was running is marked failed as "interrupted" so a rerun is decided afresh.

```mermaid
stateDiagram-v2
    [*] --> receiving: created
    [*] --> skipped: already imported
    [*] --> failed: inconsistent in Artifactory
    receiving --> ready: all pieces, start
    ready --> verifying: a running slot is free (max 2)
    verifying --> uploading: manifest ok (full, repair)
    verifying --> recording: manifest ok (finish)
    verifying --> failed: manifest differs
    uploading --> recording: upload and listing ok
    uploading --> failed: refused, 409, listing differs
    recording --> done: Catalog accepts
    recording --> failed: Catalog refuses
    receiving --> cancelled: cancel or 24 h idle
    verifying --> failed: restart (interrupted)
    uploading --> failed: restart (interrupted)
    recording --> failed: restart (interrupted)
    done --> [*]
    skipped --> [*]
    failed --> [*]
    cancelled --> [*]
```

## 6. Data model (Catalog)

```mermaid
erDiagram
    Model ||--|{ ModelVersion : owns
    Model ||--|| ModelSummary : "summarised by"
    ModelVersion ||--o{ VersionFile : lists
    ModelVersion ||--o{ StoredDocument : holds
    ModelVersion ||--|{ ImportRecord : "recorded by"
    ModelVersion ||--o{ Ref : "pointed to by"
    PersonalToken }o--|| CatalogSetting : "lifetime from"
    Model {
        text model_id
    }
    ModelVersion {
        text commit
        text state "imported or removed"
        text license
        int downloads "null when unknown"
    }
    ImportRecord {
        text imported_by
        time imported_at
        text signing_key_fingerprint
        text outcome "imported, repaired, skipped"
    }
    PersonalToken {
        text value_hash
        text scope "import only"
        time expires_at
    }
```

The models list reads only `ModelSummary` (one row per model with the latest imported version), never the documents, which is how it meets the target of under 1 second for 95% of requests at 1,000 models (NFR2). A store writes the version, files, documents, summary row and trail row in one transaction.

## 7. Retention

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Administrator
    participant P as portal
    participant S as artifactory-service
    participant K as catalog
    participant A as Artifactory

    Admin->>P: open retention page
    P->>S: versions past the period (default 365 days)
    S->>K: imported versions older than the period
    S-->>P: list (minus recent keeps)
    Admin->>P: Remove one version (confirm)
    P->>S: decision: remove
    S->>S: store decision first
    S->>A: delete the version's files (404 counts as gone)
    alt delete fails
        S-->>P: failed, version stays listed, try again
    else deleted
        S->>K: mark version removed (documents deleted, record and trail kept)
        S-->>P: done
    end
```

Nothing is ever removed without a decision for that version, and there is no bulk action. A removed version can be imported again; the Catalog then reinstates it with a new trail row.

## 8. Security: who may reach what

```mermaid
flowchart LR
    subgraph Outside["Outside the server"]
        Person["Person"]
        CLI["modelhub import"]
    end
    subgraph Edge["Published: port 443 only"]
        Proxy["proxy: TLS"]
    end
    subgraph Internal["Internal Docker network (not published)"]
        Portal
        AS["artifactory-service"]
        Cat["catalog"]
        DB[("PostgreSQL")]
    end
    Person -->|"Keycloak session cookie"| Proxy
    CLI -->|"personal import token"| Proxy
    Proxy --> Portal
    Proxy -->|"/v1/imports only"| AS
    Portal -->|"person's Keycloak token"| Cat
    Portal -->|"person's Keycloak token"| AS
    AS -->|"service token (client credentials)"| Cat
    AS -->|"checks personal token with"| Cat
    Cat --> DB
    AS --> DB
```

| Caller | Credential | May do |
|---|---|---|
| Person in the portal | Keycloak sign-in; the portal's server holds the tokens, the browser only a session cookie | browse, search, fetch instructions, make personal tokens |
| Administrator | Keycloak role `modelhub-admin` | retention decisions, token lifetime, trusted keys |
| CLI | Personal token made in the portal; import only; 90 days by default; shown once; stored as a keyed hash | import |
| `artifactory-service` | Keycloak client credentials (`modelhub-artifactory-service`) | write to the Catalog, remove marking, list versions |

Other protections: secrets only as files under `/run/secrets`; containers non-root, read-only, capabilities dropped; the Artifactory credential lives only in `artifactory-service`; each service's database user reaches only its own schema; the Catalog's user cannot update or delete trail rows; images are scanned and pinned by digest.

## 9. How the images get to the server

```mermaid
flowchart TB
    GH["GitHub Actions: build, scan, sign"] --> Pack["Signed server pack: images, Compose file, proxy config, operator script, guide"]
    Pack -->|"scanned hand-over across the air gap"| Verify["Server: verify signature"]
    Verify --> Registry["Internal container registry"]
    Registry --> Compose["docker compose up"]
    Compose --> Stack["proxy, portal, catalog, artifactory-service, PostgreSQL"]
```

No container downloads anything while running. The single-file program and offline packs are released as today.

## 10. Upgrade and return

```mermaid
flowchart TD
    U1["Verify and load new server pack"] --> U2["Note the running image tags"]
    U2 --> U3["Stop the stack (60 s grace)"]
    U3 --> U4["Change tags in the Compose file"]
    U4 --> U5["Start: database steps run under a lock"]
    U5 --> U6{"Health checks green?"}
    U6 -->|yes| U7["Sign in and check the list"]
    U6 -->|no| R1["Return: stop"]
    R1 --> R2["Put the noted tags back"]
    R2 --> R3["Start: previous version, data intact"]
```

The previous images stay on the server and in the registry. Database changes only add; data is never removed in the same release that stops using it.

## 11. Targets that shaped the design

| Area | Target |
|---|---|
| Models list | under 1 second for 95% of requests at 1,000 models and 10,000 versions, with 20 people at once |
| Findability | a model appears the moment its store commits |
| Large imports | bundles up to 200 GB; 100 GB in under 4 hours on a 1 Gbit/s link (to be measured on a real Artifactory); memory at or below 8 GB at peak |
| Restart | an import stopped at any moment and rerun gives a correct, complete result |
| Availability | business hours; back within 4 business hours of a failure noticed |
| Offline | no part connects to the internet while running |
| Stack | Python 3.12, FastAPI, psycopg 3 with plain SQL, PostgreSQL 16, Authlib (portal sign-in), PyJWT (token check), httpx (CLI), Debian-based images |
| Sizing | server minimum about 4 cores and 16 GB; database volume 100 GB; import working volume 500 GB |

## 12. What is not decided or not covered

- **Artifactory's Machine Learning layout:** JFrog's pages do not say where files are stored or how they are listed and deleted. The gateway discovers paths by listing; the stand-in's checklist lists every behaviour to confirm on a real Artifactory (open item X1). Its version must be 7.77.1 or later (X2).
- **Keycloak:** the clients `modelhub` and `modelhub-artifactory-service` and the realm role `modelhub-admin` must be created by its administrators (X3). "Signed-in people keep working if Keycloak is down" holds only while their access token is valid.
- **Old-folder import (FR8):** designed as a reserved option, not built; the old model store has no signature to check.
- **Backup:** left to a later phase; data is on named volumes so a stop-and-copy backup works.
- **Walking skeleton:** with no code, it is a paper trace spread over the units; a running end-to-end slice comes when building starts.
- **Defaults to confirm:** personal-token lifetime 90 days and 20 active tokens per person; retention 365 days; 16 MiB per stored document; two imports at once.
- **Unit order for building:** the engine follows the dependency graph (stand-in and common first, then catalog, artifactory-service, portal, import-cli, platform), which differs slightly from the Bolt plan's order; the dependencies are the same.

## 13. Where to find the detail

| Topic | Document |
|---|---|
| Why and what | `ideation/intent-capture/`, `ideation/scope-definition/` |
| Requirements and acceptance criteria | `inception/requirements-analysis/requirements.md` |
| Components and decisions (ADR-001 to ADR-010) | `inception/domain-design/` |
| Units and dependencies | `inception/units-generation/` |
| Contracts C1 to C8 (APIs, errors, retries) | `inception/contract-design/contract-summary.md` |
| Delivery plan and outside dependencies | `inception/delivery-planning/` |
| Per-unit entities, rules (BR), specs | `construction/<unit>/functional-design/` |
| Per-unit quality targets and designs | `construction/<unit>/nfr-requirements/`, `nfr-design/` |
| Hosting, Compose, install and upgrade steps | `construction/platform/infrastructure-design/` |
