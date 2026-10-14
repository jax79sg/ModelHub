# NFR Requirements Questions: portal

Context: "NFR" means quality targets. The portal is the web app people use. Already settled and reused here: the stack (Python 3.12, FastAPI, uvicorn), list speed (NFR2: under 1 second at 1,000 models, measured on the server), up to 20 people at once, recovery within 4 business hours, sign-in done by the portal's server, sessions in memory for 8 hours idle. Two choices are yours.

My defaults for this unit (not questions): pages are server-rendered with no outside files; every page except sign-in and health needs a session; the security headers of the prototype stay (content security policy with no inline script, nosniff, no referrer, frame denial); forms are checked against forged requests; nothing is stored in the browser except the theme; page weight is under 300 KB without pictures.

## Q1. Which library should the portal use for the Keycloak sign-in?

Why we ask: the standard browser sign-in (OpenID Connect with a code exchange) is easy to get subtly wrong, and the portal holds the people's tokens.

- Option A, Authlib (a maintained OpenID Connect client for FastAPI). Pros: written by specialists; handles discovery, the code exchange with a proof key (PKCE), state and token refresh. Cons: a larger dependency.
- Option B, our own code on top of httpx and PyJWT (the same libraries the shared `common` uses). Pros: fewer dependencies; full control. Cons: security-sensitive code that we write and must review ourselves.
- Recommendation: A.

A. Option A: Authlib
B. Option B: own code on httpx and PyJWT
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. Which browsers must the portal work in?

Why we ask: this fixes what the pages and the small amount of script may use, and what the tests cover.

- Option A, the current and previous version of Chrome, Edge and Firefox (the usual organisation desktop browsers). Pros: modern features; small test set. Cons: Safari is not covered.
- Option B, A plus Safari. Pros: also covers Mac users. Cons: a larger test set.
- Recommendation: A, with B if Mac users are expected.

A. Option A: current and previous Chrome, Edge and Firefox
B. Option B: A plus Safari
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A
