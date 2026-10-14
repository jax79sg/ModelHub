# Functional Design Questions: common

Context: `common` is the small shared library that the three server-side units (`catalog`, `artifactory-service`, `portal`) build into their images. It checks a Keycloak token and role (contract C6), reads secrets and settings (C7), writes structured logs (C7) and offers the health check (C7). It holds no business rules and no data of its own. The requirement it carries is FR6.5, and it serves FR3.1, FR4.1, FR6.4 and NFR5b. Contracts C6 and C7 already fix the token claims, the log fields, the secret file names and the health answers, so the questions are only about what those contracts leave open.

## Q1. How should the library get Keycloak's signing keys?

Why we ask: it must verify a token's signature without calling Keycloak on every request, and Keycloak can change its keys. C6 says the keys are fetched when the service starts and refreshed when an unknown key id appears. What is open is what happens when Keycloak cannot be reached.

- Option A, keep the last good keys and keep accepting tokens signed by them; refuse tokens signed by a key never seen when Keycloak cannot be reached; report `keycloak: down` in the ready check but stay ready. Pros: people already signed in keep working (FR3.8); an outage does not stop the portal. Cons: a revoked key is trusted until the next refresh succeeds.
- Option B, refuse every token when the keys cannot be refreshed after a set time (for example 1 hour). Pros: shorter exposure to a revoked key. Cons: a long Keycloak outage logs everyone out and stops imports.
- Option C, refuse every token the moment Keycloak cannot be reached. Pros: strictest. Cons: contradicts FR3.8; unacceptable for a tool that must keep working.
- Recommendation: A.

A. Option A: keep the last good keys; refuse unseen keys; stay ready
B. Option B: stop accepting tokens after a set time
C. Option C: refuse everything when Keycloak is unreachable
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. How should a secret that changes on disk be handled?

Why we ask: secrets are read from files (C7). A rotated password (for example the database password) changes the file while the service is running.

- Option A, read each secret once at start-up; a changed secret takes effect when the service restarts. Pros: simplest; no surprises mid-request. Cons: a rotation needs a restart (which the upgrade procedure already does).
- Option B, re-read the file whenever a connection fails with a refusal, then retry once. Pros: rotation without restart. Cons: more behaviour to test; hides a wrong password behind a retry.
- Recommendation: A.

A. Option A: read once at start-up
B. Option B: re-read when a connection is refused
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. What should the library do when a required secret or setting is missing or unreadable at start-up?

Why we ask: a service that starts without its database password would fail later in a confusing way (NFR5b forbids the message from showing the value).

- Option A, refuse to start: list the names of every missing or unreadable item (never values) in one message and exit with a failure, so the container's restart policy and the health check show it at once. Pros: the failure is early and clear. Cons: none that matter.
- Option B, start anyway and report `down` in the ready check for the parts that need it. Pros: the service can say what is wrong over HTTP. Cons: a half-working service is easy to miss.
- Recommendation: A.

A. Option A: refuse to start, naming every missing item
B. Option B: start and report down in the ready check
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. How much of a failed request should the logs and error answers reveal?

Why we ask: NFR5b says secrets never appear in logs or error messages, and C6 says a bad token gets `401 token_invalid` with no detail. The open choice is the log side: the real reason (expired, wrong audience, tampered) helps the operator.

- Option A, the answer to the caller is always the same minimal text; the log line names the reason as a fixed code (`expired`, `wrong_audience`, `bad_signature`, `unknown_key`, `missing`, `malformed`) and never includes any part of the token. Pros: operators can diagnose; the caller learns nothing. Cons: none that matter.
- Option B, log only "token rejected". Pros: simplest. Cons: operators cannot tell an expired token from an attack.
- Recommendation: A.

A. Option A: minimal answer; reason code in the log
B. Option B: log only "token rejected"
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. How should the "ready" check decide a dependency is down?

Why we ask: the platform polls it (FR6.5) and C7 says the answer lists database, Keycloak and Artifactory as `ok` or `down`. A check that calls the dependency on every poll adds load and can itself time out.

- Option A, each service registers its own checks (a function per dependency); the library calls each at most once every 10 seconds, with a 2-second limit, and caches the result. A check that times out counts as `down`. Pros: cheap; a poll never blocks long; each service names only what it uses. Cons: the answer can be up to 10 seconds old.
- Option B, call every check on every poll. Pros: always fresh. Cons: load and slow polls.
- Recommendation: A.

A. Option A: registered checks, cached for 10 seconds, 2-second limit
B. Option B: check on every poll
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A
