# Requirements Analysis Questions

Context: these questions follow the approved intent, feasibility and scope documents (`ideation/`). They fix what the system must do and how well. Answers you gave earlier are not asked again; where a question builds on one, it says which. The corner cases (a half-finished import, two imports at once, odd file names, a service being down) I will write into the requirements myself with sensible defaults, so you can correct them there instead of answering them here.

## Q1. Where should everything the CLI downloads besides the model files live?

Why we ask: the CLI also keeps a model's README and pictures, Hugging Face's responses saved as they came, a checksum manifest, and the signed bundle description files. Artifactory's Hugging Face repository hands every file in a model's folder to anyone who downloads that model, so extra files placed there would travel with the model.

A. In the database (text as JSON or Markdown, pictures as stored data)
B. In a second, plain-file Artifactory repository next to the Hugging Face one
C. Inside the Hugging Face repository, next to the model files
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. What must the import record each time?

Why we ask: you want every import traceable (intent capture Q3). This fixes what "traceable" contains.

A. Who ran it, when, and on which computer
B. The bundle: its name, its checksum, and the fingerprint of the key that signed it
C. The tool version and the result of the checks made before the upload
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q3. Which roles does the portal need once people sign in through Keycloak?

Why we ask: roles decide who can see the import trail and who can change settings such as retention. No roles have been defined yet.

A. No roles: everyone who signs in can browse and fetch
B. Roles: viewer (browse and fetch), reviewer (also sees the import trail and licence flags), administrator (also changes settings)
C. The roles in B, and some models can be limited to certain groups
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. What does "who imported it" mean?

Why we ask: the trail has to name someone, and the CLI runs on a computer, not in the portal.

A. The person's own Keycloak sign-in; the CLI asks them to sign in before importing
B. The operating-system user on the import computer
C. The Artifactory account (token) the CLI used
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. If Artifactory has a model's files but the database has no record of it, what should the next import of that model do?

Why we ask: an import that stops halfway can leave the two stores out of step (feasibility risk R9). You said a model already imported is skipped (feasibility Q10 and Q13); this covers the half-imported case.

A. Finish the missing part automatically and say so in the report
B. Stop for that model and report it so a person decides
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q6. What must people be able to do in the portal beyond what the prototype does today? (select all that apply)

Why we ask: today the prototype filters by task, library, licence, language and size; sorts; and shows a model card, files and versions, and commit history. Anything added here becomes a requirement.

A. Filter and sort by when a model was imported and by whom
B. Search the text of model cards
C. See a warning on models that have no licence
D. Nothing beyond today's features
E. Not yet defined
X. Other (please specify)

[Answer]: A, B

## Q7. How fast should the portal's model list respond when the store holds 1,000 models?

Why we ask: a measurable target is needed for the quality requirements. The earlier planning figure was about 1,000 models (feasibility Q5 left the real size open).

A. Under 1 second
B. Under 3 seconds
C. Under 10 seconds
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q8. How available must the system be?

Why we ask: this decides whether one server is enough. You chose Docker Compose on one server (intent capture Q10), which cannot survive the server itself being down.

A. Business hours only; the server may be down for upgrades and repairs
B. Always on except for planned, announced windows (about 99% over a month)
C. Higher than that, which would need more than one server and changes the Compose-on-one-server choice
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q9. When a model version passes its retention period, what should happen?

Why we ask: you said a retention period applies (feasibility Q3) but not what it does. The choice decides how destructive it is.

A. It is removed from Artifactory and marked removed in the database; the import trail stays
B. It is hidden in the portal only; the files are kept
C. It is listed for a person to decide each time
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q10. How long is the retention period?

Why we ask: the rule needs a number to be testable. It can also be a setting that each site changes.

A. 1 year
B. 3 years
C. 7 years
D. Not yet defined; make it a setting with no default
X. Other (please specify)

[Answer]: A

## Q11. How strong must the import trail's protection be?

Why we ask: security is one of your top qualities (scope definition Q6). The trail is the proof of who imported what.

A. Ordinary database rows; people with database access could change them
B. Append-only: the application can never change or delete a trail row
C. Append-only, and each row is chained to the one before by a checksum so any change can be detected
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q12. Where should the passwords and tokens for Artifactory, the database and Keycloak be kept?

Why we ask: secrets must not sit in the images or in the project files. Where they live shapes the container layout.

A. In files or Docker secrets on the server that only the services can read
B. In an existing secrets manager (please name it)
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q13. With no roles (Q3), who may decide what happens to a model version that has passed its retention period (Q9)?

Why we ask: you chose to have a person decide each time (Q9 C) but also no roles (Q3 A), so by default anyone who signs in could decide. Retention decisions can lead to removing files.

A. Anyone who signs in
B. Only people named in a list kept in the settings
C. Add a single administrator role just for this and other settings
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q14. Your trail answer (Q2 B) lists only the bundle details, but you also said who imported it (Q4) and, earlier, who, when and from which bundle (intent capture Q3). Should the trail record more than the bundle?

Why we ask: Q2 could be read as "the bundle only" or as "the bundle, in addition to what was already agreed".

A. Yes: who, when and on which computer, plus the tool version and check results, as well as the bundle details
B. Who and when as well as the bundle details, but not the tool version and check results
C. The bundle details only
D. Not yet defined
X. Other (please specify)

[Answer]: A
