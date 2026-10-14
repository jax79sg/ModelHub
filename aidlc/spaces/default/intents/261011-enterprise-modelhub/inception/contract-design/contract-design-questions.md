# Contract Design Questions

Context: a contract is the agreement across a boundary: what crosses it, in what shape, how, and what happens when something goes wrong. From the unit dependencies there are these boundaries:

- **C1** `import-cli` (U6) to `artifactory-service` (U4): sending a verified package and starting and following an import.
- **C2** `artifactory-service` (U4) to `catalog` (U2): looking up and recording versions, files, documents and trail rows.
- **C3** `portal` (U5) to `catalog` (U2): reading everything the portal shows.
- **C4** `portal` (U5) to `artifactory-service` (U4): the retention screens and the trusted-key screen.
- **C5** `artifactory-service` (U4) to Artifactory: what we rely on Artifactory to do (not ours; we write down our assumptions).
- **C6** The Keycloak token every unit checks: what must be in it.
- **C7** What every server-side unit offers the server: a health check, log lines and where secrets are read from (the shared `common` unit).

No part of this system is offered to outside programs beyond Artifactory's own repository address, which standard tools already use, so there is no public API of ours to define.

The questions are about the choices that matter most. The rest I will fill in with sensible defaults (the owner of each contract is the unit that provides it; additive changes are safe because consumers ignore unknown fields) and write down for you to correct.

## Q1. What should the units use to talk to each other?

Why we ask: this fixes the style of contract (C1 to C4). The existing web app already uses HTTP with JSON, and a written HTTP contract (OpenAPI) is easy to read, test and mock.

- Option A, HTTP with JSON, described in OpenAPI. Pros: the existing web app and test tools already speak it; easy to read and to test against the stand-in; works through the organisation's usual proxies. Cons: not the most compact for very large transfers (handled separately in Q2).
- Option B, gRPC. Pros: compact and fast, strict typing. Cons: new for this project; harder to read and debug; the web app would need an adapter.
- Recommendation: A.

A. Option A: HTTP with JSON, described in OpenAPI
B. Option B: gRPC
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. How should a verified package travel from the CLI to the import service?

Why we ask: this is the biggest transfer in the system (files over 100 GB, from a computer that may be on a slow link) and the open question OQ2. It must survive being interrupted, never hold a whole model in memory, and let the service check the signature again (decision 5 of Domain Design).

- Option A, send the bundle exactly as the CLI already makes it: its pieces, its description file and its signature. Each piece is one request, checked by its checksum, and a stopped transfer resumes at the first missing piece. The service joins and unpacks the pieces itself and re-verifies with the same code the CLI uses. Pros: reuses the existing, tested bundle format and checking; resumes at piece level; the signed description is exactly what the service verifies. Cons: the service needs disk space for the pieces on its way through (it removes each as it is unpacked); a model from the old folder (FR8) must first be made into a bundle with the existing `bundle` command.
- Option B, send the files one by one, in chunks, with resume. Pros: also works for the old folder without a bundle. Cons: a new upload protocol to design and test; the signed manifest still has to be sent and checked, so the signed description travels anyway.
- Option C, send everything as one stream. Pros: simplest. Cons: an interruption at 99 GB means starting again; no useful progress; not acceptable for files this size.
- Recommendation: A.

A. Option A: the bundle's pieces, description file and signature
B. Option B: the files, one by one, in chunks, with resume
C. Option C: one stream
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. Does the CLI wait for the import to finish, or start it and ask how it is going?

Why we ask: after the pieces arrive, the service unpacks them, re-verifies, uploads to Artifactory (which can take hours for a large model) and records the result (open question OQ5).

- Option A, start it and ask. The CLI starts the import, gets a job number, and asks for progress until it ends; it can stop and ask again later. Pros: no request open for hours; a dropped connection does not lose the import; matches the import-job record the service already keeps. Cons: the CLI must poll.
- Option B, wait on one request. Pros: simple. Cons: a request open for hours is likely to be cut by a proxy or a timeout; if the CLI is closed the person does not know the result.
- Recommendation: A.

A. Option A: start the import and ask for progress
B. Option B: wait on one request
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. How does the CLI sign a person in on a computer with no web browser or internet?

Why we ask: this is open question OQ1. The import computer is on the air-gapped side and may have no browser.

- Option A, device sign-in: the CLI shows a short code and an address; the person opens the address on any device that can reach Keycloak (their own laptop or phone inside the network), enters the code and approves; the CLI then receives the token. Pros: no password typed into the CLI; works on a browserless computer; Keycloak supports it. Cons: needs some device with a browser that can reach Keycloak.
- Option B, type username and password into the CLI. Pros: works anywhere. Cons: Keycloak must allow that mode, which its own documentation discourages; the password passes through the CLI.
- Option C, a personal token made in the portal and pasted into the CLI. Pros: no browser on the import computer. Cons: a long-lived secret to store and rotate.
- Recommendation: A.

A. Option A: device sign-in
B. Option B: username and password typed into the CLI
C. Option C: a personal token made in the portal
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q5. How does Keycloak say a person is an administrator?

Why we ask: every unit needs to recognise an administrator (FR4.2) from the token alone. This is the second open question from requirements.

- Option A, a Keycloak realm role named `modelhub-admin`, assigned by the Keycloak administrators, carried in the token. Pros: simple, standard, one name to check. Cons: your Keycloak administrators must create and assign it.
- Option B, membership of a Keycloak group, for example `/modelhub/admins`. Pros: fits if people are already managed by group. Cons: the group claim must be switched on in the token.
- Option C, let the design decide. The contract states a name and your Keycloak administrators can map it.
- Recommendation: A.

A. Option A: a realm role named `modelhub-admin`
B. Option B: a group, for example `/modelhub/admins`
C. Option C: let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q6. How should the contracts be versioned?

Why we ask: the portal and the services are upgraded together on one server, but the CLI is installed on import computers and may be older or newer than the server for a while.

- Option A, a version in every address (`/v1/...`). A breaking change gets `/v2/...` and the old one is served for one release. Additive changes (new fields) are safe because consumers ignore unknown fields. Pros: an old CLI keeps working through an upgrade; easy to test. Cons: serving two versions briefly.
- Option B, no versioning; everything is upgraded together. Pros: nothing extra. Cons: an old CLI breaks on upgrade with an unclear error.
- Recommendation: A. At minimum it applies to the CLI's contract (C1); the others follow the same rule for consistency.

A. Option A: a version in every address
B. Option B: no versioning
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q7. You chose a personal token made in the portal (Q4 C). Who issues that token?

Why we ask: this decides whether Keycloak stays the one place that issues and revokes sign-ins, and whether the system needs a second token system.

- Option A, Keycloak issues it. The portal asks Keycloak for a long-lived "offline" token for the signed-in person and shows it once; the CLI stores it in a file only that person can read and uses it to get short-lived tokens. Pros: Keycloak remains the only issuer, so the same token check works everywhere; revoking and expiry are managed in Keycloak. Cons: your Keycloak administrators must allow offline tokens for the portal and set how long an idle one lives.
- Option B, the system issues its own tokens. The Catalog stores a hash of each token and checks it. Pros: independent of Keycloak's settings. Cons: a second token system to build and defend; "who" then comes from our table and not from Keycloak.
- Recommendation: A.

A. Option A: Keycloak issues it (an offline token)
B. Option B: the system issues its own tokens
C. Not yet defined
X. Other (please specify)

[Answer]: B
