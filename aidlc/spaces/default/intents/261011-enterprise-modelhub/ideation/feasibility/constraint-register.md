# Constraint Register

Constraints on the work described in `intent-statement` (`ideation/intent-capture/`). "Source" points to your answers in `feasibility-questions.md` (Q1 to Q13), to your answers in `intent-capture-questions.md` (written IQ), to the request, or to the evidence list (E1 to E10) in `feasibility-assessment.md`.

## Organisational Constraints

| ID | Constraint | Source | Effect |
|----|------------|--------|--------|
| CO-1 | You alone decide scope and priority; others give advice only | IQ12, IQ19 | No approval path to design around |
| CO-2 | The Artifactory administrators need only a repository and a service account for the CLI | IQ20 | The design must not need more of them |
| CO-3 | A design is needed within about a month | Q7 | Fits a design-only plan; limits what can be researched on real systems |
| CO-4 | No other organisational limit is known: existing hardware only, change approvals and freezes were not selected | Q6 (none known) | Nothing further recorded |
| CO-5 | No Artifactory is available now to build or test against, and when one will be is not known | IQ17, Q11 | The design must include an emulation and plan for acceptance late or never |
| CO-6 | The team is comfortable with Docker and Docker Compose | Q4 | Less step-by-step handover guidance needed |
| CO-7 | Private and gated models, and automatic updates of imported models, are left out of the first version | IQ14 | Keeps the scope to public models imported once |

## Technical Constraints

| ID | Constraint | Source | Effect |
|----|------------|--------|--------|
| CT-1 | The new parts run as Docker containers under Docker Compose on one Linux server that already has Docker | IQ9, IQ10, Q8 | One host, no orchestration platform to design for |
| CT-2 | The existing Artifactory stays outside the containers | IQ9 | The new parts only connect to it |
| CT-3 | The database is PostgreSQL, run as a container | IQ7 | Needs a data volume and a backup plan |
| CT-4 | Sign-in uses Keycloak | IQ16, IQ21 | The web app connects to Keycloak; roles come from it |
| CT-5 | The server has no internet, so container images must reach it through an internal container registry | Q1, request (air-gapped) | An image pipeline from the online side to the registry is part of the design |
| CT-6 | Logging or monitoring already exists centrally | Q1 | The new parts should report into it rather than bring their own |
| CT-7 | The import computer can reach both Artifactory and the database | Q2 | No import service in front of the database is required |
| CT-8 | The upload to Artifactory uses JFrog's `jf hf upload` | Q9 | The import computer needs the JFrog CLI, Python 3 and a supported `huggingface_hub` (E1) |
| CT-9 | Artifactory supports `huggingface_hub` only up to 1.19.0, and Xet transfers up to 1.18.0 | E3 | The upload cannot use the CLI's own `huggingface_hub` 2.2 or newer (E9) |
| CT-10 | Artifactory has a limited Hugging Face API: only download and upload are supported through `jf hf`, and Spaces are not supported | IQ5, E1, E7 | Listing, search and model pages must come from the database and web app |
| CT-11 | Names deployed to Artifactory follow Hugging Face rules: organisation names use letters, numbers and single hyphens; model names use letters, numbers, hyphens, underscores and periods; revisions use letters, numbers, hyphens and periods | E5 | Some real model or branch names may be refused; imports use the commit hash as the revision |
| CT-12 | Re-uploading the same version overwrites it, and needs the Delete/Overwrite permission or Artifactory answers 409 | E6 | The import must check first, because the rule is to skip a model that is already there |
| CT-13 | A repository created now uses the Machine Learning layout; the older layout is deprecated | E4 | Design against the new layout only |
| CT-14 | The emulation stands in for the Hugging Face upload and download plus other calls the CLI and web app need, and is not delivered | IQ22, IQ24 | Emulation is a build-and-test tool and out of the delivered container list |

## Regulatory And Legal Constraints

| ID | Constraint | Source | Effect |
|----|------------|--------|--------|
| CR-1 | Each model's licence must be kept and shown with the model | Q3 | The database stores the licence; the portal shows it |
| CR-2 | A retention period applies to how long old model versions are kept; its length is not given | Q3 | A rule and a mechanism are needed; the length is an open item (A5 in `raid-log.md`) |
| CR-3 | A scan of imported files before use was not selected | Q3 | No scanner is required in the first version |
| CR-4 | No data-residency or other compliance regime has been named | Q3, Q6 (none stated) | Nothing further recorded |

## Assumptions And Open Questions

- The Artifactory version, and whether a local Hugging Face repository with the Machine Learning layout can be created on it, are not known [assumption]
- The storage size to plan for is not given (Q5); the earlier planning figure of about 1,000 models with up to 10 versions each, some over 100 GB, is used until it is [assumption]
- The retention period in CR-2 has no length [assumption]
- The air-gapped import computer can have the JFrog CLI, Python 3 and `huggingface_hub` 1.19.0 or older installed offline [assumption]
