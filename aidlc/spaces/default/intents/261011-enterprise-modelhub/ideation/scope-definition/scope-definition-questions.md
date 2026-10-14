# Scope Definition Questions

Context: these questions follow the intent statement (`ideation/intent-capture/`) and the feasibility documents (`ideation/feasibility/`). They are about what the first enterprise version contains and in what order it is built. The workflow you approved stops at the architecture, so a separate question (Q4) asks how much of it to design now.

## Q1. What is the smallest first version that is still useful?

Why we ask: it fixes the minimum scope everything else is measured against. The parts are: the CLI importing into Artifactory with a record in the database, the web app as the portal with Keycloak sign-in, and bringing in the models already in the old folder store.

A. The CLI imports into Artifactory and records the model in the database; the web app is not changed yet
B. A, plus the web app as the portal reading the database, with Keycloak sign-in
C. B, plus importing the models already in the old folder store
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q2. Which of these also belong in the first version? (select all that apply)

Why we ask: these are the extra capabilities the intent and feasibility answers raised. Anything not picked is recorded as left for a later version.

A. A rule for how long old model versions are kept (a retention period)
B. Backup and restore for the database and the stored files
C. Reporting into the central logging and monitoring that already exist
D. A documented way for automated pipelines to fetch models (they would use Artifactory's own download)
E. None of these; they can wait
X. Other (please specify)

[Answer]: A, C

## Q3. In what order should the work be done?

Why we ask: the least known part is the Artifactory upload and its emulation (feasibility risks R1 to R3). The order decides whether that is tackled first or last.

A. Risk-first: the Artifactory upload path and its emulation first, because they are the least certain
B. Value-first: the database and the portal first, because people see them
C. Dependency-first: the data model, then the import, then the portal
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q4. How much of the architecture should the design cover now?

Why we ask: your approved plan stops at the architecture, with no code. The design can describe the whole system or only the first version's parts.

A. The whole architecture, with the build order marked so the first version can be built from it
B. Only the parts of the first version chosen in Q1 and Q2
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. Are there hard dates tied to particular capabilities?

Why we ask: you said the design is needed within about a month (feasibility Q7). A date attached to one capability changes the order.

A. No; only the date for the design itself
B. Yes, a particular capability has its own date (please name it and the date)
C. Not yet defined
X. Other (please specify)

[Answer]: C

## Q6. Which qualities matter most for "enterprise level"? (select all that apply)

Why we ask: these steer the quality targets in the next stages and what the design protects first.

A. Security: sign-in, roles, and a trail of who imported what
B. Reliability: backups, and repairing an import that stopped halfway
C. Operability: central logging and monitoring, simple upgrades
D. Speed of import and download for very large models
X. Other (please specify)

[Answer]: A, C

## Q7. What happens to the prototype web app that reads the old folder?

Why we ask: the portal replaces it (intent capture Q8), but the new app may start from it or from scratch.

A. It is grown into the portal, keeping what works and replacing the folder reading with the database
B. It stays running until the portal is ready, then is retired
C. The portal is a new app built from scratch
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q8. Importing the models already in the old folder store: in the first version or later?

Why we ask: in feasibility Q12 you said the old folder's models are imported with the same CLI. In Q1 above you chose a smallest version (B) that does not include importing them (option C of Q1 does). Both can be true if it comes later; this question makes sure.

A. Later: it is part of the whole architecture (Q4) but not of the first version
B. In the first version: change the smallest version to include it (Q1 option C)
C. Not yet defined
X. Other (please specify)

[Answer]: A
