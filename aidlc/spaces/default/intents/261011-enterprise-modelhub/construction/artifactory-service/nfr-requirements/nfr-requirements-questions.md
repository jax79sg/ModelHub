# NFR Requirements Questions: artifactory-service

Context: "NFR" means quality targets. This is the container that receives bundles, re-checks them, uploads to Artifactory, records through the Catalog and runs retention. Already settled and reused here: the stack (Python 3.12, FastAPI, psycopg 3), recovery within 4 business hours, up to 20 people at once, restart safety (NFR4), memory at or below 8 GB at peak for any file size (NFR7) and no internet connection while running (NFR8). Two numbers are still missing and they are yours to give: how big the largest model is, and how long a big import may take.

My defaults for this unit (not questions): at most 2 imports run at once (service design BR1.10); retries and waits as in the import rules; the import service's calls to the Catalog have a 5-second connect and 30-second read limit; an idle import is cancelled after 24 hours; the Artifactory credential and Keycloak client secret come from the secret files only.

## Q1. How large can one model's bundle be?

Why we ask: the server must have disk space to receive the pieces (and the unpacked files) before they are uploaded. The planning figure says "some over 100 GB". A number is needed to size the disk and to refuse an import that would not fit (rule BR1.20).

- Option A, up to 200 GB per bundle. Pros: covers the models over 100 GB with room. Cons: the working disk must be about 450 GB with two imports at once.
- Option B, up to 500 GB. Pros: room for very large models. Cons: about 1.1 TB of working disk.
- Option C, up to 100 GB. Pros: small disk. Cons: the planning figure says some are over it.
- Recommendation: A.

A. Option A: up to 200 GB per bundle
B. Option B: up to 500 GB per bundle
C. Option C: up to 100 GB per bundle
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. How long may a large import take?

Why we ask: a time target needs a link speed and is the only way to know whether the design (pieces, unpacking, uploading) is fast enough. The CLI sends to the service, and the service uploads to Artifactory; both steps count.

- Option A, a 100 GB model imports in under 4 hours from the first piece sent to "done", measured on a 1 Gbit/s link with the real Artifactory. Pros: a clear, testable target. Cons: depends on the real Artifactory and links, which are not available now; it is checked later with the real systems.
- Option B, under 24 hours. Pros: easy to meet. Cons: a very loose target.
- Option C, no time target; only progress and resume are required. Pros: honest while the links are unknown. Cons: nothing to test against.
- Recommendation: A, recorded as a target to be measured when a real Artifactory exists.

A. Option A: 100 GB in under 4 hours on a 1 Gbit/s link
B. Option B: under 24 hours
C. Option C: no time target
D. Not yet defined
X. Other (please specify)

[Answer]: A
