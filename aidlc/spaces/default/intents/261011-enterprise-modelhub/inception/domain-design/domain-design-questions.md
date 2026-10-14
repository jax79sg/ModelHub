# Domain Design Questions

Context: Domain Design names the building blocks of the system: the code you will write, not the databases or servers it uses. How the blocks are packaged into containers is decided in the next stage. From the requirements and the existing tool, the blocks I see are:

- **Package source:** reads a verified bundle, or an old model-store folder, and presents one model version ready to import (the existing verify and unpack code, reused).
- **Importer:** in the CLI; decides skip, repair, name checks, retries, the report and the exit status.
- **Sign-in:** in the CLI; signs the person in through Keycloak.
- **Artifactory gateway:** uploads with `jf hf upload`, and checks for and deletes versions in Artifactory.
- **Catalog:** owns the model information, the stored documents and the import trail; answers searches and filters.
- **Retention:** owns the retention setting and the keep or remove decisions.
- **Portal:** the web app; the pages, the sign-in, the safe rendering of model cards.
- **Artifactory stand-in:** for building and testing only.

Five choices decide where the boundaries between them fall. For each I give the options, what each costs, and what I recommend. The choice is yours.

## Q1. Is there a separate import service, or does the CLI do the whole import itself?

Why we ask: when you chose the container list (intent capture Q9) one listed part was an "import service". Later you said the import computer reaches both Artifactory and the database and uploads with `jf hf upload` (feasibility Q2 and Q9), which reads as the CLI doing the work. The two do not match, so this settles it.

- Option A, the CLI does the whole import: it verifies the bundle, uploads to Artifactory, and records the result through the data interface. Pros: no extra container, and what you chose in Q9 stays as chosen. Cons: every import computer needs the JFrog CLI, Python 3 and the older `huggingface_hub` (risk R1). Reversibility: easy to add a service later.
- Option B, a server-side import service does the upload and the recording, and the CLI only hands it the verified files. Pros: the older Python environment lives once, in a container, instead of on every import computer. Cons: one more container; the CLI must send very large files to it; it departs from your `jf hf upload` choice on the import computer. Reversibility: moderate.
- Recommendation: A. It follows what you chose, and R1 stays a known, contained cost. Revisit if installing the older environment on import computers proves painful.

A. Option A: the CLI does the whole import (no import service)
B. Option B: a server-side import service does the upload and recording
C. Not yet defined
X. Other (please specify)

[Answer]: B

## Q2. Does the importer write to the database directly, or through a data interface?

Why we ask: this decides whether database passwords sit on import computers and where the rules (such as writing the version and its trail row in one transaction) live.

- Option A, through a data interface (the Catalog as a service the CLI calls with the person's Keycloak token). Pros: the database password stays on the server; the server sees who is calling, so the trail's "who" is checked rather than self-reported; the rules live in one place. Cons: one more part to run and a network hop. Reversibility: moderate (the interface becomes the contract).
- Option B, directly into the database. Pros: simplest, fewest parts. Cons: a database login on every import computer, which conflicts with keeping secrets off such machines (FR6.4); "who" is whatever the CLI claims; the portal would repeat the same rules. Reversibility: hard once many computers hold database logins.
- Recommendation: A. It is what "interface to the data" in your container list (intent capture Q9) describes.

A. Option A: through a data interface that checks the Keycloak token
B. Option B: directly into the database
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. Does the portal read the database directly, or through the same data interface?

Why we ask: the portal and the importer both need the model information, and the portal also records retention decisions.

- Option A, the portal uses the same data interface as the importer. Pros: one set of rules, one place for queries such as search and filters, one database login (the interface's). Cons: the portal depends on that interface being up. Reversibility: easy.
- Option B, the portal reads the database itself. Pros: one fewer call in each page. Cons: two programs with database logins and two copies of the query and permission rules.
- Recommendation: A, for the same reasons as Q2.

A. Option A: through the same data interface
B. Option B: directly from the database
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. Is retention its own building block or part of the Catalog?

Why we ask: retention decides, then deletes files from Artifactory, then marks the version removed in the database (FR5). That reaches outside the database.

- Option A, Retention is its own block. It owns the setting and the decisions, and calls the Artifactory gateway to delete and the Catalog to mark. Pros: the Catalog stays purely about information; deleting files is isolated and easy to test with the stand-in. Cons: one more block, and the two-step "delete then mark" lives in Retention (FR5.6). Reversibility: easy.
- Option B, Retention is part of the Catalog. Pros: fewer blocks, one transaction for the marking. Cons: the Catalog would now call Artifactory and hold deletion rights, mixing information with a destructive action.
- Recommendation: A.

A. Option A: Retention is its own building block
B. Option B: Retention is part of the Catalog
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. One Artifactory gateway for the whole system, or one for the CLI and one for the server?

Why we ask: with the import service from Q1, both uses of Artifactory now run on the server: the import service uploads with `jf hf upload`, and Retention deletes and inspects through Artifactory's own web interface. The naming rules, the repository layout and the "does this version exist" check apply to both.

- Option A, one gateway block with two ways of working (upload through `jf hf`; inspect and delete through Artifactory's web interface). Pros: one place that knows Artifactory's naming rules, layout and quirks, and one thing for the stand-in to be tested against. Cons: one block carries two kinds of call. Reversibility: easy.
- Option B, two blocks (an uploader and an inspector and remover). Pros: each is smaller. Cons: the naming rules and layout would be written twice and could drift apart.
- Recommendation: A.

A. Option A: one gateway block
B. Option B: two blocks
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q6. Who verifies the bundle: the CLI only, or the import service as well?

Why we ask: with the import service from Q1, the CLI verifies a bundle on the import computer (as it does today) and then hands the files over. The service could trust that, or check again itself. Security is one of your top qualities.

- Option A, the CLI only. Pros: the existing verification is reused unchanged and the service stays simpler. Cons: the service trusts whatever an authenticated CLI sends, so a changed or unsigned file would be imported if a CLI were modified or misused.
- Option B, the CLI and the service. The CLI checks first so it fails fast; the service then checks the signature against its own list of trusted keys and every file against the signed manifest before uploading. Pros: the trail's "signing key" is checked on the server, not claimed by the CLI. Cons: the service needs its own trusted-key list and the checking code (reused from the CLI's library) and does the work twice. Reversibility: easy.
- Recommendation: B.

A. Option A: the CLI only
B. Option B: the CLI and the import service
C. Not yet defined
X. Other (please specify)

[Answer]: B
