# Functional Design Questions: portal

Context: `portal` is the web app people use, grown from the prototype in `web/` (package `hubsite`). It must require a Keycloak sign-in, read everything through the Catalog (never a folder or the database), keep the prototype's pages and look, and add the import filters, text search, the import trail, the fetch instructions, the personal-token page and the administrator screens for retention and trusted keys. It never serves model files; they come from Artifactory. Requirements: FR3 to FR3.3, FR3.6 to FR3.8, FR4.1, FR4.6; also FR5.3 to FR5.7 and FR1.14 screens. The prototype keeps its safe rendering (FR3.7). The Catalog, retention and key interfaces are fixed (contracts C2, C3, C4).

## Q1. How does the sign-in work in the portal?

Why we ask: the portal must send the signed-in person's Keycloak token to the Catalog and the retention service (contracts C2, C4), and sessions must survive a Keycloak outage for people already signed in (FR3.8).

- Option A, the portal's own server does the sign-in with Keycloak (the standard browser redirect flow), keeps the person's tokens on the server side, and gives the browser only a session cookie (secure, HTTP-only, same-site). The portal's server calls the Catalog and retention service with the person's token. Pros: tokens never reach the browser; a Keycloak outage does not log out people whose session is valid; fits the prototype's server-rendered pages. Cons: the portal keeps session data in memory or a small store.
- Option B, a single-page app in the browser signs in with Keycloak and calls the services itself. Pros: no server session. Cons: tokens sit in the browser; the prototype would have to be rewritten as a single-page app; the Catalog would need to allow browser calls from the portal's address.
- Recommendation: A.

A. Option A: the portal's server signs in and holds the tokens
B. Option B: the browser signs in and calls the services
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. Where are sessions kept, and for how long?

Why we ask: with Option A above, the server remembers who is signed in. A restart of the portal should not log everyone out if it can be avoided, and sessions should not last forever.

- Option A, in the portal's memory; a restart signs people out; a session lasts as long as the Keycloak refresh token allows, up to 8 hours idle (settings). Pros: simplest; no extra storage. Cons: a portal restart (such as an upgrade) signs everyone out; one copy of the portal only.
- Option B, in an encrypted cookie (the session data is held in the cookie itself, sealed with a secret key). Pros: survives restarts; no server storage. Cons: the cookie can be large; tokens are in the browser, though sealed.
- Recommendation: A. People simply sign in again after an upgrade, which happens rarely.

A. Option A: in memory, 8 hours idle
B. Option B: sealed cookie
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q3. What does the portal show for a model whose version was removed?

Why we ask: the Catalog keeps the record, file list and trail of a removed version but deletes the README and pictures (Catalog design, FDQ6 B). The portal must show something sensible.

- Option A, the model's page still opens: it shows the card fields, the file list marked "removed", the import trail including the removal decision, and a clear banner "this version was removed on <date> by <name>; the README is no longer stored". It is hidden from the models list unless the person ticks "show removed". Pros: nothing is lost from the history; no dead ends. Cons: a removed version's page is mostly empty.
- Option B, a removed version disappears from the list and its page answers "not found". Pros: simplest. Cons: the trail's links lead nowhere; confusing.
- Recommendation: A.

A. Option A: page still opens with a clear banner; hidden from the list unless asked
B. Option B: not found
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q4. What are the "how to fetch" instructions (FR3.6)?

Why we ask: each model page must show how to fetch the model from Artifactory with standard tools: the repository address, the model id and the revision, and a link to Artifactory.

- Option A, three copy-ready snippets with the model id and commit filled in: `jf hf download`, the Python `huggingface_hub` call with the endpoint set to Artifactory's Hugging Face address, and the plain endpoint setting for tools that read `HF_ENDPOINT`. The repository key and Artifactory's address are portal settings. Pros: covers JFrog's supported route and the common library; direct. Cons: the exact command forms must be checked against a real Artifactory (they follow JFrog's documentation).
- Option B, only the repository address and the model id and revision as plain facts, no commands. Pros: nothing to get wrong. Cons: people must work out the commands themselves.
- Recommendation: A.

A. Option A: three copy-ready snippets plus the facts
B. Option B: only the facts
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. How does the portal show a failed retention or trusted-key action to an administrator?

Why we ask: removing a version is the one destructive action. The screen must show progress, the failure when Artifactory refuses (FR5.6) and what to do next.

- Option A, an action page per version with a confirmation step ("Remove <model> <commit>? This deletes its files from Artifactory and cannot be undone"), the result shown after (done, failed with the reason, or files deleted but not marked, with a "try again" button for the last two), and no bulk action. Pros: matches the one-version-at-a-time rule; safe. Cons: removing many versions is slow (intended).
- Option B, a table with checkboxes and one "remove selected" button. Pros: fast for many. Cons: contradicts the rule that each version is decided each time (FR5.4).
- Recommendation: A.

A. Option A: one version at a time with a confirmation and a clear result
B. Option B: bulk selection
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A
