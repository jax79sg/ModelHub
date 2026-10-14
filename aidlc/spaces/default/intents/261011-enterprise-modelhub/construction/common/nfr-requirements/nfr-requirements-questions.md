# NFR Requirements Questions: common

Context: "NFR" means quality targets. `common` is a small shared library with token checking, secrets, logging and health helpers, so only security and the technology stack apply (per-kind rules give a library just the security and technology-stack documents). The technology for the server units is asked in the `artifactory-stand-in` questions and reused here.

My defaults for this unit (not questions): checking one token adds less than 5 milliseconds on top of the signature work (a cached key); a key refresh never blocks other requests for more than the 5-second connect limit; the library keeps no data on disk; secrets are never printed; tokens signed with RS256 or ES256 only; a 60-second clock allowance.

## Q1. Which library should check the token signatures?

Why we ask: this is the most security-sensitive code in the system (requirements NFR5).

- Option A, PyJWT with the `cryptography` package (already used by the CLI for signing). Pros: small, widely used, well reviewed; restricts algorithms explicitly; reuses a dependency already in the project. Cons: key-set (JWKS) fetching is written by us (small).
- Option B, Authlib. Pros: includes key-set fetching and more of the OpenID flow. Cons: a much larger library; the portal's sign-in could use it too, which is a reason for or against.
- Recommendation: A for the token check in `common`; the portal's browser sign-in flow is decided at its own NFR step.

A. Option A: PyJWT with cryptography
B. Option B: Authlib
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. Which Python versions must `common` support?

Why we ask: the server units run in containers whose Python we choose, but `common` is also imported by the test tools on the build machines.

- Option A, Python 3.12 only (the container version). Pros: simplest; newest security fixes. Cons: build machines need 3.12.
- Option B, 3.10 and later (as the CLI and prototype). Pros: runs on today's build machines. Cons: a wider matrix to test.
- Recommendation: B for now, with the images using 3.12, so the existing CI (3.10 and 3.12) covers it.

A. Option A: 3.12 only
B. Option B: 3.10 and later
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: B
