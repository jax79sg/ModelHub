# Intent Backlog

Prioritized proto-units for the work in `scope-document.md`, using MoSCoW (Must, Should, Could, Won't this time). The order follows your sequencing choice, dependency-first (SQ3 C). Sources are your answers in `scope-definition-questions.md` (SQ), `feasibility-questions.md` (FQ) and `intent-capture-questions.md` (IQ). Proto-units become units of work in a later stage.

## Prioritized List

| ID | Proto-unit | Priority | Depends on | Source |
|----|------------|----------|------------|--------|
| B1 | Data model and the PostgreSQL database (models, versions, files, licences, import trail) | Must | none | IQ3, IQ7, SQ1 B, SQ3 C |
| B2 | Artifactory stand-in (build and test only, not delivered) | Must | none | IQ17, IQ22, IQ24, SQ3 C |
| B3 | Import: verify a bundle, upload with `jf hf upload`, record in the database, skip a repeated commit | Must | B1, B2 | IQ6, FQ9, FQ10, FQ13, SQ1 B |
| B4 | Portal: the prototype web app grown to read the database, link to Artifactory, and sign in with Keycloak | Must | B1, B3 | IQ8, IQ21, SQ1 B, SQ7 A |
| B5 | Container hosting: Docker Compose on the Linux server, images through the internal registry | Must | B1, B3, B4 | IQ9, IQ10, FQ1, FQ8 |
| B6 | Retention rule for old model versions | Should | B1, B3 | FQ3, SQ2 A |
| B7 | Reporting into central logging and monitoring | Should | B3, B4, B5 | FQ1, SQ2 C, SQ6 C |
| B8 | Import of the models already in the old folder store | Could (designed now, built later) | B3 | FQ12, SQ8 A |
| B9 | Backup and restore of the database and stored files | Won't this time (designed later) | B1, B5 | not picked in SQ2 |
| B10 | A documented way for pipelines to fetch models | Won't this time | B3 | not picked in SQ2 |
| B11 | Private and gated models; automatic updates of imported models | Won't | none | IQ14 |
| B12 | Scanning of imported files | Won't | none | FQ3 (not selected) |

## Order Of Work

Dependency-first (SQ3 C): **B1** the data model first, then **B2 and B3** (the stand-in and the import), then **B4** the portal, then **B5** hosting, then **B6 and B7**. B8 follows the first version. B9 and B10 are not planned.

## Why This Order

- B1 is first because the import, the portal and the retention rule all read or write it.
- B2 has no dependency and unblocks B3, which cannot be tried without an Artifactory (IQ17). It is also the least certain part (`raid-log` R2, R3), so the design stage looks at it early even though the sequencing choice is dependency-first.
- B4 follows B3 because the portal needs something in the database to show.

## Assumptions And Open Questions

- The MoSCoW priorities come from the capabilities you picked in SQ1 and SQ2, not from a scoring exercise; no effort estimates exist yet [assumption]
- B9 and B10 as "Won't this time" may change once the design shows what they cost [assumption]
