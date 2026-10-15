# Requirement-To-Unit Map

> Carried unchanged from the approved design (`aidlc/spaces/default/intents/261011-enterprise-modelhub/inception/units-generation/unit-of-work-story-map.md`); the build uses the same seven units and the same dependency order.


There are no user stories in this plan, so every row is keyed by a functional requirement (`FR`) from `requirements.md`. Each row names the unit that implements it. "Also touches" lists other units that contribute but are not the primary owner. Unit IDs and directories are from `unit-of-work.md`.

## Functional Requirements

| Requirement | Unit | Directory | Also touches |
|-------------|------|-----------|--------------|
| FR1 | U6 | u6-import-cli | U4 |
| FR1.1 | U4 | u4-artifactory-service | U6 |
| FR1.2 | U6 | u6-import-cli | U4, U1 |
| FR1.3 | U4 | u4-artifactory-service | U2 |
| FR1.4 | U4 | u4-artifactory-service | U6 |
| FR1.5 | U4 | u4-artifactory-service | U2 |
| FR1.6 | U4 | u4-artifactory-service | U2 |
| FR1.7 | U4 | u4-artifactory-service | none |
| FR1.8 | U4 | u4-artifactory-service | none |
| FR1.9 | U6 | u6-import-cli | U4 |
| FR1.10 | U6 | u6-import-cli | none |
| FR1.11 | U6 | u6-import-cli | none |
| FR1.12 | U4 | u4-artifactory-service | none |
| FR1.13 | U6 | u6-import-cli | none |
| FR1.14 | U4 | u4-artifactory-service | U5 (the administrator's key screen) |
| FR2 | U2 | u2-catalog | none |
| FR2.1 | U2 | u2-catalog | none |
| FR2.2 | U2 | u2-catalog | none |
| FR2.3 | U2 | u2-catalog | U4 |
| FR2.4 | U2 | u2-catalog | none |
| FR2.5 | U2 | u2-catalog | none |
| FR2.6 | U2 | u2-catalog | none |
| FR2.7 | U2 | u2-catalog | U5 |
| FR2.8 | U2 | u2-catalog | U5 |
| FR3 | U5 | u5-portal | U2 |
| FR3.1 | U5 | u5-portal | U1 |
| FR3.2 | U5 | u5-portal | U2 |
| FR3.3 | U5 | u5-portal | U2 |
| FR3.4 | U2 | u2-catalog | U5 |
| FR3.5 | U2 | u2-catalog | U5 |
| FR3.6 | U5 | u5-portal | none |
| FR3.7 | U5 | u5-portal | none |
| FR3.8 | U5 | u5-portal | U2 |
| FR4 | U4 | u4-artifactory-service | U5 |
| FR4.1 | U5 | u5-portal | U1 |
| FR4.2 | U4 | u4-artifactory-service | U1 |
| FR4.3 | U4 | u4-artifactory-service | U5, U1 |
| FR4.4 | U2 | u2-catalog | U5 |
| FR4.5 | U2 | u2-catalog | U4 |
| FR4.6 | U5 | u5-portal | U2 |
| FR5 | U4 | u4-artifactory-service | U5 |
| FR5.1 | U4 | u4-artifactory-service | U5 |
| FR5.2 | U4 | u4-artifactory-service | U2 |
| FR5.3 | U4 | u4-artifactory-service | U5 |
| FR5.4 | U4 | u4-artifactory-service | U5 |
| FR5.5 | U4 | u4-artifactory-service | U2 |
| FR5.6 | U4 | u4-artifactory-service | U2 |
| FR5.7 | U4 | u4-artifactory-service | U2 |
| FR6 | U7 | u7-platform | all server-side units |
| FR6.1 | U7 | u7-platform | none |
| FR6.2 | U7 | u7-platform | none |
| FR6.3 | U7 | u7-platform | U2 |
| FR6.4 | U7 | u7-platform | U1 |
| FR6.5 | U1 | u1-common | U7 |
| FR6.6 | U7 | u7-platform | U2, U4 (database upgrades) |
| FR7 | U3 | u3-artifactory-stand-in | none |
| FR7.1 | U3 | u3-artifactory-stand-in | none |
| FR7.2 | U3 | u3-artifactory-stand-in | none |
| FR7.3 | U3 | u3-artifactory-stand-in | none |
| FR8 | U6 | u6-import-cli | U4 |
| FR8.1 | U6 | u6-import-cli | U4 |

## Rows That Span Several Units (Cross-Cutting Concerns)

- **Sign-in and roles (FR3.1, FR4.1 to FR4.3, FR1.2).** The token check is written once in U1 and used by U2, U4 and U5; the CLI's sign-in is in U6.
- **Secrets, logging and health (FR6.4, FR6.5).** The helpers are in U1; each unit uses them; U7 wires them into the containers.
- **Import (FR1).** Split between U6 (verify, send, report) and U4 (re-verify, decide, upload, record), with U2 storing the result.
- **Retention (FR5).** Decisions and removal in U4, screens in U5, version state and the trail in U2.

## Quality Requirements (for information)

| Quality requirement | Mainly in |
|---------------------|-----------|
| NFR1 findability within 1 hour | U4, U2 |
| NFR2 portal list under 1 second | U2, U5 |
| NFR3 business-hours availability | U7 |
| NFR4 restart | U4, U6 |
| NFR5 security | U1, U2, U4, U5, U7 |
| NFR6 operability | U1, U7 |
| NFR7 capacity | U2, U4 |
| NFR8 offline | U7 |
| NFR9 testability | U3, all |
| NFR10 import platforms | U6 |

## Order Of Work Within Each Unit

Only the order inside a unit is stated here, not between units.

- **U1:** token check, then secrets and configuration, then logging and health.
- **U2:** the data model and its upgrades, then storing a version with its trail row, then the models list with filters and sort, then search, then marking a version removed.
- **U3:** the upload calls, then listing and checksums, then delete, then the documented rules, then the assumptions and checklist.
- **U4:** the Artifactory gateway, then the job record and the lock, then the re-verification, then the skip, repair and full import, then the trusted-key list, then retention.
- **U5:** the Catalog-backed list and card, then sign-in, then import and importer filters, then search, then fetch instructions, then the retention and key screens.
- **U6:** sign-in, then reading a package, then sending and the report, then the old-folder reading.
- **U7:** the images, then the Compose file with secrets and the data volume, then health and logging, then the registry path, then the upgrade and return steps.

## Coverage Verification

- Every functional requirement from `requirements.md` has one row above: FR1 to FR8 and all their sub-requirements, 61 rows in all.
- Every unit has rows: U1 (1 row), U2 (13), U3 (4), U4 (20), U5 (9), U6 (8), U7 (6), counting each row under its primary unit; 61 in all.
- No requirement is left without a unit. There are no uncovered items.
