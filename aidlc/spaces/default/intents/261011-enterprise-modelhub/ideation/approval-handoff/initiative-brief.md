# Initiative Brief

A one-page summary of the Ideation phase for the work in `intent-statement`. Full detail is in the documents named in each section.

## Intent And Problem

Models downloaded by the CLI end up in a folder on one air-gapped computer, which the prototype web app reads. People elsewhere in the organisation cannot find or reuse them, and nothing records what was imported and approved (`intent-capture/intent-statement.md`). The organisation wants the CLI to put models into the enterprise store (Artifactory), the model information to live in a PostgreSQL database, the web app to become the portal, and the whole to be hosted in Docker containers.

Success means: a model can be found and downloaded within an hour of its import; every import is traceable (who, when, which bundle, which signing key); and standard Hugging Face download tooling works against the store.

## Market Validation

Not done. Market research was not part of the approved plan, and the work extends your own tool inside your own organisation, so a market view was not needed. Nothing in this brief depends on one.

## Feasibility And Risk Highlights

Verdict: **feasible, with four conditions** (`feasibility/feasibility-assessment.md`).

- The upload you chose (`jf hf upload`) needs Python 3 and a `huggingface_hub` no newer than 1.19.0, while the CLI needs 2.2 or newer. The import computer therefore carries a second, older environment (risk R1).
- No real Artifactory is available to test against, so it is emulated; the emulation may differ from the real system (R2, R3).
- Artifactory refuses some model and branch names that Hugging Face allows (R4).
- The two stores, Artifactory and PostgreSQL, can disagree after a half-finished import (R9).
- The store's size and the retention period are not yet given (R6, R10).

The full list of ten risks, six assumptions, one issue and six dependencies is in `feasibility/raid-log.md`, and the constraints in `feasibility/constraint-register.md`.

## Scope Boundary

(`scope-definition/scope-document.md`, `scope-definition/intent-backlog.md`)

- **Designed now (the whole system):** model import, the metadata database, the portal, container hosting, the Artifactory stand-in, the retention rule, reporting into central logging and monitoring, and importing the old folder's models.
- **First build:** the data model, the Artifactory stand-in, the import, the portal with Keycloak sign-in, container hosting, the retention rule and central logging, in that dependency-first order.
- **Built later:** importing the old folder's models, and backup and restore.
- **Left out:** private and gated models, automatic updates, scanning imported files, datasets, Spaces, and a documented way for pipelines to fetch models.
- **Qualities that matter most:** security and operability.

## Concept Visuals

None. Rough mock-ups were not part of the plan. The portal grows from the existing prototype web app, so its look is already visible there.

## Team Plan

Team formation was not part of the plan. You decide scope and priority alone; the Artifactory administrators, the security and compliance team and the teams using the models give advice only (`intent-capture/stakeholder-map.md`). The Artifactory administrators need only a repository and a service account for the CLI. You are comfortable with Docker and Docker Compose.

## Go / No-Go Recommendation

**Go**, to Inception. The idea is feasible on the evidence available, the scope is bounded, and the main risks are named with responses. You accepted the intent and scope, the risks and their responses, and the time commitment (`approval-handoff/approval-handoff-questions.md`, Q1 to Q3).

Two things to keep in view while moving on: the least certain part is the Artifactory emulation, and that is where the design stage should look first; and the store size and retention period are still undefined.

## Assumptions And Open Questions

- The real Artifactory behaves as JFrog's documentation says and is version 7.77.1 or newer with a local Hugging Face repository in the Machine Learning layout [assumption]
- The import computer can carry the JFrog CLI, Python 3 and `huggingface_hub` 1.19.0 or older beside the single-file `modelhub` program [assumption]
- The storage size to plan for is the earlier planning figure (about 1,000 models, up to 10 versions each, some over 100 GB) [assumption]
- The retention period has no length yet [assumption]
