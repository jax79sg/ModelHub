# Decision Log

Every decision made during Ideation, in order, with where it was made. "IQ" is `intent-capture-questions.md`, "FQ" is `feasibility-questions.md`, "SQ" is `scope-definition-questions.md`, "AQ" is `approval-handoff-questions.md`.

## Plan And Working Method

| ID | Decision | Made at |
|----|----------|---------|
| D1 | Use a custom, design-focused plan based on classic: 13 stages, stopping at the architecture with no code; reviews off because no sub-agents are to be used | Plan approval at the start |
| D2 | Answer stage questions by being guided through them in the conversation | IQ answer-mode choice |

## Intent Capture

| ID | Decision | Made at |
|----|----------|---------|
| D3 | The problem is both: models stuck in one folder, and no auditable record of what was imported and approved | IQ1 C |
| D4 | The users are ML engineers, the platform team, security and compliance reviewers, and automated systems | IQ2 |
| D5 | Success is findable and downloadable soon after import, full traceability, and standard Hugging Face tooling working | IQ3 |
| D6 | The triggers are the prototype working, an audit or compliance need, and more teams asking | IQ4 |
| D7 | Artifactory's Hugging Face API is limited (no advanced calls), as its website documents | IQ5 |
| D8 | After verifying a bundle the CLI uploads to Artifactory and records in the database, replacing the folder | IQ6 A |
| D9 | The database is PostgreSQL in a container | IQ7 A |
| D10 | The web app becomes the organisation's portal with single sign-on | IQ8 A |
| D11 | Only the new parts run in containers; the existing Artifactory stays outside; Docker Compose on one server | IQ9 A, IQ10 A |
| D12 | The stakeholders are the owner, the Artifactory administrators, security and compliance, and the teams using models; the owner decides alone and the others advise | IQ11, IQ12 A, IQ19 B |
| D13 | The Artifactory administrators need only a repository and a service account | IQ20 A |
| D14 | No reporting beyond the decision record | IQ13 A |
| D15 | Private and gated models and automatic updates are left out of the first version | IQ14 |
| D16 | "Soon after import" means within an hour | IQ15 B |
| D17 | Sign-in uses an OpenID Connect provider, Keycloak | IQ16 B, IQ21 A |
| D18 | No Artifactory is available now, so it is emulated; the emulation covers Hugging Face upload and download plus other calls the CLI and web app need, treats JFrog's documentation as a starting point, and is a build-and-test stand-in that is not delivered | IQ17, IQ22 B, IQ23 B, IQ24 A |
| D19 | The standard download command (and upload for the CLI) is all that standard tooling needs; listing, search and model pages come from the database and web app | IQ18 A |
| D20 | Two assumptions were accepted as labelled assumptions (Artifactory version; JFrog's documented limits) | IQ assumption confirmation |

## Feasibility

| ID | Decision | Made at |
|----|----------|---------|
| D21 | The new parts connect to an internal container registry and to central logging or monitoring | FQ1 |
| D22 | The import computer reaches both Artifactory and the database | FQ2 A |
| D23 | Each model's licence must be kept and shown, and a retention period applies | FQ3 |
| D24 | The team is comfortable with Docker | FQ4 A |
| D25 | The store size is not yet defined | FQ5 D |
| D26 | No organisational limits are known; a design is needed within about a month | FQ6 D, FQ7 B |
| D27 | A Linux server that already has Docker runs the containers | FQ8 A |
| D28 | The upload uses JFrog's `jf hf upload` | FQ9 A |
| D29 | A model whose same version is already imported is skipped and the rest of the list carries on | FQ10, FQ13 B |
| D30 | The models in the old folder store are imported with the same CLI | FQ12 A |
| D31 | When a real Artifactory will be available is not known | FQ11 C |

## Scope Definition

| ID | Decision | Made at |
|----|----------|---------|
| D32 | The smallest first version is the CLI import plus the portal with Keycloak sign-in | SQ1 B |
| D33 | The retention rule and reporting into central logging and monitoring also belong in the first version | SQ2 A, C |
| D34 | The order of work is dependency-first: data model, then import, then portal | SQ3 C |
| D35 | The design covers the whole architecture, with the build order marked | SQ4 A |
| D36 | No capability has its own date | SQ5 C |
| D37 | Security and operability matter most | SQ6 A, C |
| D38 | The prototype web app is grown into the portal | SQ7 A |
| D39 | Importing the old folder's models comes after the first version | SQ8 A |

## Approval And Handoff

| ID | Decision | Made at |
|----|----------|---------|
| D40 | The intent and scope are accepted as recorded | AQ1 A |
| D41 | The main risks and the plan's responses are accepted | AQ2 A |
| D42 | There is time to take the work through requirements and design | AQ3 A |
| D43 | Learnings: none of the notes from Intent Capture, Feasibility and Scope Definition were kept as lasting rules | Learnings step at each stage |
