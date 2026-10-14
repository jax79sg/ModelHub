# RAID Log

Risks, Assumptions, Issues and Dependencies for the work in `intent-statement` (`ideation/intent-capture/`). Evidence references (E1 to E10) are in `feasibility-assessment.md`; constraint references (CO, CT, CR) are in `constraint-register.md`.

## Risks

| ID | Risk | Likelihood | Impact | Response |
|----|------|------------|--------|----------|
| R1 | The upload step needs a second, older Python environment (`huggingface_hub` 1.19.0 or older) (CT-8, CT-9). **Reduced in Domain Design (DQ1 B, ADR-001):** it now lives once, in the import service's container, not beside the CLI on every import computer. What remains: that container must carry the JFrog CLI, Python 3 and the pinned older library | Low | Medium | Keep the version pinned and written down in the container's definition |
| R2 | The emulated Artifactory behaves differently from the real one (CO-5, CT-14), so code that works against the emulation fails on the real system | Medium-High | High | Keep the emulation to what JFrog documents; write down every behaviour it assumes; plan an acceptance run on the real system as soon as one exists |
| R3 | No real Artifactory is ever available to test against (Q11 "not known") | Medium | High | Treat the first run on a real instance as a risk to plan for, with a short checklist of the documented behaviours to confirm |
| R4 | Real model or branch names are refused by Artifactory's naming rules (CT-11, E5) | Medium | Medium | Check names before upload and report which models cannot be stored; keep the original name in the database |
| R5 | A re-import of an existing version overwrites it or fails with 409 instead of being skipped (CT-12, E6) | Medium | Medium | The import checks the database and Artifactory first and skips a model whose same commit is already there (Q10, Q13) |
| R6 | The storage size is undefined, so disk, database and backup are mis-sized (Q5) | Medium | Medium | Size to the earlier planning figure; state the formula so it can be rescaled when a number is given |
| R7 | Container images cannot reach the air-gapped server in time or at all because the transfer path to the internal registry is unclear (CT-5) | Medium | High | Describe the image pipeline in the infrastructure design and confirm with the registry's owner |
| R8 | JFrog changes the Hugging Face support (as it did when it deprecated the legacy layout in June 2026, E4) and the design goes out of date | Medium | Medium | Record the Artifactory and client versions the design was checked against |
| R9 | Two stores (Artifactory and PostgreSQL) disagree after a partial import, for example the files upload but the database write fails | Medium | High | Decide in functional design which is the source of truth and how an interrupted import is detected and repaired |
| R10 | The retention period has no length (CR-2, A5), so a retention mechanism cannot be tested | Medium | Low | Make the period a setting and note it for requirements |

## Assumptions

All are unconfirmed and labelled as assumptions.

- A1: JFrog's documentation describes the real Artifactory correctly [assumption]
- A2: The Artifactory is version 7.77.1 or newer with a local Hugging Face repository in the Machine Learning layout [assumption]
- A3: The import computer can have the JFrog CLI, Python 3 and `huggingface_hub` 1.19.0 or older installed offline [assumption]
- A4: The earlier planning figure (about 1,000 models, up to 10 versions each, some over 100 GB) holds for the enterprise store [assumption]
- A5: The retention period will be given later [assumption]
- A6: The internal container registry can receive images that were built online and carried across on drives [assumption]

## Issues

- I1: No Artifactory is available to build or test against (CO-5). This is already true, so it is an issue, not a risk.

## Dependencies

- D1: The Artifactory and its administrators, for a repository and a service account for the CLI (CO-2)
- D2: Keycloak, for sign-in (CT-4)
- D3: The internal container registry (CT-5)
- D4: Central logging or monitoring (CT-6)
- D5: JFrog CLI, Python 3 and a supported `huggingface_hub` on the import computer (CT-8, CT-9)
- D6: The existing `modelhub` CLI and web app, whose download record and model store are what the new import reads (Q12)
