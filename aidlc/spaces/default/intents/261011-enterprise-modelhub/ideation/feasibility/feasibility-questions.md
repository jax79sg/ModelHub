# Feasibility Questions

Context: these questions follow the intent statement (`intent-statement`, in `ideation/intent-capture/`). The research on what Artifactory offers for Hugging Face models is done by me from JFrog's documentation and is written up after your answers.

## Q1. Which other systems must the new parts connect to, besides Artifactory and Keycloak? (select all that apply)

Why we ask: the new parts run in containers on an air-gapped server, so anything they must reach or be loaded from shapes the design.

A. An internal container image registry (the images for the new parts must be loaded into it for the server to run them)
B. Central logging or monitoring (for example Prometheus and Grafana, or an ELK stack)
C. An existing backup system for databases and files
D. None of these
X. Other (please specify)

[Answer]: A, B

## Q2. From where will the CLI's import run, and what can that computer reach?

Why we ask: the CLI is to upload files to Artifactory and record the model information in the database (intent capture Q6 and Q7). That only works if the computer running it can reach both, or if the design puts a helper next to the database.

A. It is on the same network as both Artifactory and the database and can reach both
B. It can reach Artifactory but not the database, so a small import service next to the database must do the database part
C. It can reach neither; imports are done from another machine that can
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. Are there rules about what must happen to imported models? (select all that apply)

Why we ask: rules like these become requirements and decide which parts the architecture needs.

A. Each model's licence must be kept and shown with the model
B. Imported files must be scanned for malicious content (for example by JFrog Xray or another scanner) before people can use them
C. There is a retention period for how long old model versions must be kept
D. None known
X. Other (please specify)

[Answer]: A, C

## Q4. How comfortable is the team with Docker and Docker Compose?

Why we ask: it sets how much step-by-step guidance the design and its handover need.

A. Comfortable; we run containers today
B. Some experience; clear instructions are enough
C. New to containers; step-by-step guidance is needed
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. How much do you expect to store?

Why we ask: earlier work on this project planned for up to about 1,000 models with up to 10 versions each, some over 100 GB. The enterprise store may differ, and the size drives disk, database and backup choices.

A. The same sizing as before (up to about 1,000 models, up to 10 versions each, some over 100 GB)
B. Smaller: tens of models, under 1 TB in all
C. Larger: several thousand models or tens of TB
D. Not yet defined
X. Other (please specify)

[Answer]: D

## Q6. What organisational limits apply to this work? (select all that apply)

Why we ask: limits like these decide how much new software and hardware the design can assume.

A. Only hardware and licences that already exist can be used
B. Changes to the air-gapped environment need an approval process (for example a change board or security sign-off)
C. A freeze or competing priority limits when changes can be made
D. None known
X. Other (please specify)

[Answer]: D

## Q7. Roughly how far away is the date by which the design is needed?

Why we ask: it decides how much detail is realistic and what to do first.

A. There is no fixed date
B. Within a month
C. Within a quarter
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q8. What will run the containers?

Why we ask: it decides which operating-system details the design has to cover (for example how images are loaded without internet access).

A. A Linux server that already has Docker installed
B. A Linux server that still has to be set up
C. A Windows server
D. Not yet decided
X. Other (please specify)

[Answer]: A

## Q9. How should the CLI upload files into Artifactory?

Why we ask: the CLI's online side needs `huggingface_hub` 2.2 or newer, but JFrog's documentation supports Artifactory only with `huggingface_hub` up to 1.19.0 (Xet transfers up to 1.18.0). The upload therefore cannot simply reuse the library the CLI uses today.

A. Use JFrog's own `jf hf upload`, which needs Python 3 and a supported `huggingface_hub` on the computer that runs the import
B. Call Artifactory's web address directly from the CLI, with no Hugging Face library on the import side (less documented by JFrog, so riskier)
C. Run the upload in a small separate container that has a supported `huggingface_hub`; the CLI hands it the files
D. Let the design stage decide
X. Other (please specify)

[Answer]: A

## Q10. What should happen to the models already in the existing folder store?

Why we ask: you chose to replace the folder (intent capture Q6). The models already unpacked there either move across or are left behind.

A. Import them into the new store, using the same CLI
B. Start fresh; the old folder is retired
C. Not yet defined
X. Other (please specify)

[Answer]: X. If it's already there and not a different version, the action should stop right.

## Q11. When could a real Artifactory be available to test against?

Why we ask: you said none is available now and it has to be emulated (intent capture Q17). How long that lasts decides how much risk sits in the emulation.

A. Before building starts
B. Only for final acceptance testing near the end
C. It is not known
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q12. Your answer to Q10 says an import should stop when the model is already there and is not a different version. Do the models already in the old folder store get imported at all?

Why we ask: Q10 as answered covers what a repeated import does. It does not say whether the old folder's models are brought across or left behind.

A. Yes, import them with the same CLI (the rule you gave then applies to each one)
B. No, start fresh; the old folder is retired
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q13. When an import finds the same model and the same version (commit) already imported, what should it do?

Why we ask: "stop" could mean ending the whole run, or leaving that one model alone and carrying on with the rest of a list.

A. Stop the whole import run with a clear error naming the model
B. Skip that model, say so in the report, and carry on with the others
C. Not yet defined
X. Other (please specify)

[Answer]: B
