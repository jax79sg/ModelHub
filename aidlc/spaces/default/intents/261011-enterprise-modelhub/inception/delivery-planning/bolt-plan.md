# Bolt Plan

A **Bolt** is one build pass over a piece of the work, ending in something you can check. This plan stops at the architecture with no code, so each Bolt here is one unit of work taken through its four design runs (functional design, quality requirements, quality design, infrastructure design) and ends in four approved design documents. Choices are from `delivery-planning-questions.md` (written DPQ): dependency-first with the riskiest part early (DPQ1 A), one unit per Bolt (DPQ2 A), unit by unit (DPQ3 A), one after another (DPQ4 A).

Units are defined in `inception/units-generation/unit-of-work.md`; requirement IDs (FR, NFR) in `inception/requirements-analysis/requirements.md`; contracts (C1 to C8) in `inception/contract-design/contract-summary.md`.

## Order

| Bolt | Unit | Kind, size | Waits on | Requirements carried |
|------|------|------------|----------|----------------------|
| B1 | U1 common | library, S | nothing | FR6.5 (the token check serves FR3.1; logging and secrets serve FR6.4) |
| B2 | U3 artifactory-stand-in | service (test only), M | nothing | FR7, FR7.1, FR7.2, FR7.3 |
| B3 | U2 catalog | service, L | B1 | FR2 to FR2.8, FR3.4, FR3.5, FR4.4, FR4.5 |
| B4 | U4 artifactory-service | service, XL | B1, B2, B3 | FR1.1, FR1.3 to FR1.8, FR1.12, FR1.14, FR4, FR4.2, FR4.3, FR5 to FR5.7 |
| B5 | U5 portal | ui, L | B1, B3, B4 | FR3, FR3.1, FR3.2, FR3.3, FR3.6, FR3.7, FR3.8, FR4.1, FR4.6 |
| B6 | U6 import-cli | service, M | B4 | FR1, FR1.2, FR1.9 to FR1.11, FR1.13, FR8, FR8.1 |
| B7 | U7 platform | packaging, M | B3, B4, B5 | FR6, FR6.1 to FR6.4, FR6.6 |

This order respects the dependency list in `unit-of-work-dependency.md`. B1 and B2 depend on nothing and could swap places; `common` goes first because every later unit uses it. No Bolt departs from the dependency order, so nothing needs a justification beyond the one in `risk-and-sequencing-rationale.md`.

The quality requirements (NFR1 to NFR10) are carried by the units named in the "Quality Requirements" table of `unit-of-work-story-map.md`.

## Walking Skeleton

The team practice is to prove the pieces connect before the real features. With no code, the thinnest end-to-end path is a paper trace: one very small model going through every contract (the CLI sends it, the import service accepts and re-verifies it, uploads it, the Catalog records it, the portal shows it). It cannot be a running slice, and the first unit in dependency order (`common`) is a library, not an end-to-end slice. So the skeleton is handled this way, and is flagged for you at the gate:

- Each of B3 to B6 must include, in its design, the part of the trace it owns (a named "skeleton path" section in its functional design).
- B7 closes it: its Definition of Done includes one end-to-end walk-through of the trace across all seven units, written down and approved.
- The real-end-to-end check that the Construction phase normally demands cannot exist yet; no verification command is set (DPQ6 A).

## Bolt Entries

### B1: common (U1)
- **Included unit.** U1 common.
- **Skeleton marker.** No; supplies the token check every part of the trace needs.
- **Definition of Done.** Four design documents approved. They fix the token and role check (expired, tampered and wrong-audience tokens are named cases), how secrets are read from files and never logged, the log line shape, and the health-check helper (C6, C7).
- **Confidence hypothesis.** One shared token check can serve all three services without per-service variants.
- **Expected demo.** A written table of the checks and the error each one gives, reviewed against C6 and C7.
- **Owner.** The developer agent in this session.

### B2: artifactory-stand-in (U3)
- **Included unit.** U3 artifactory-stand-in.
- **Skeleton marker.** No; lets B4 be designed and tested without a real Artifactory.
- **Definition of Done.** Four design documents approved. They list every call it answers (upload, listing, checksums, delete), the documented rules it follows, and its list of assumptions, each with a "confirm on the real Artifactory" line (FR7.1 to FR7.3).
- **Confidence hypothesis.** The calls `jf hf upload` and `snapshot_download` make are few enough to imitate faithfully from the documentation.
- **Expected demo.** The assumptions checklist, ready to hand to whoever has access to the real Artifactory.
- **Owner.** The developer agent.

### B3: catalog (U2)
- **Included unit.** U2 catalog.
- **Skeleton marker.** Part of the trace: storing a version with its trail row.
- **Definition of Done.** Four design documents approved: the tables and their upgrades, the one-transaction store of a version and its trail row, the models list that answers in under 1 second at 1,000 models (NFR2) without reading stored documents, search, removal marking, and personal tokens (hash only, 90 days, shown once).
- **Confidence hypothesis.** One database schema supports the list, search, trail and token needs without a second store.
- **Expected demo.** The tables and the queries behind each portal screen, checked against NFR2.
- **Owner.** The developer agent.

### B4: artifactory-service (U4)
- **Included unit.** U4 artifactory-service.
- **Skeleton marker.** Part of the trace: the heart of the import.
- **Definition of Done.** Four design documents approved: re-verification of the bundle (FR1.14), the job record and per-model lock, skip, repair and full import, the gateway to Artifactory including the discover-by-listing rule for paths, the trusted-key list, and retention with delete-then-mark-removed ordering.
- **Confidence hypothesis.** An interrupted import of a very large package can always be repeated safely (NFR4) and never leaves a half-recorded model.
- **Expected demo.** A state diagram of an import job covering every failure point, and the retention decision flow.
- **Owner.** The developer agent.

### B5: portal (U5)
- **Included unit.** U5 portal.
- **Skeleton marker.** Part of the trace: the end the person sees.
- **Definition of Done.** Four design documents approved: sign-in, list with filters and sort, search, import-trail view, fetch instructions, retention and key screens for administrators only, token page, and plain messages when the Catalog or Keycloak cannot be reached.
- **Confidence hypothesis.** The prototype's code can keep its features while replacing the folder reading with the Catalog.
- **Expected demo.** Screen-by-screen description tied to the requirement IDs.
- **Owner.** The developer agent.

### B6: import-cli (U6)
- **Included unit.** U6 import-cli.
- **Skeleton marker.** Part of the trace: the start of the path.
- **Definition of Done.** Four design documents approved: personal-token storage in a file only the person can read, verifying and sending the bundle piece by piece with resume, the report and exit statuses, old-folder reading, and platform support (NFR10).
- **Confidence hypothesis.** The existing bundle code and exit statuses can be reused without change to the current commands.
- **Expected demo.** A table of the report and exit status for each outcome (skip, repair, full import, refusal, network failure).
- **Owner.** The developer agent.

### B7: platform (U7)
- **Included unit.** U7 platform.
- **Skeleton marker.** Closes the skeleton with the whole-system walk-through.
- **Definition of Done.** Four design documents approved: images for the three services and PostgreSQL, the Compose file, secrets, health checks, logging to standard output, the registry path, the data volume, and the upgrade and return steps; plus the end-to-end walk-through across all seven units.
- **Confidence hypothesis.** The whole system starts, runs and rolls back on one Linux server with no internet access while running (NFR8).
- **Expected demo.** The server layout diagram and the written walk-through.
- **Owner.** The developer agent.

## Construction Settings

- Iteration: unit by unit, one after another (`unit-major`, `serial`), which is the default for new workflows (DPQ3 A, DPQ4 A).
- Staffing: this session does all the work; no team ownership (DPQ6 A).
- Verification command: not set now; it will be asked at the first checkpoint (DPQ6 A).
