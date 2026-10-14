# Infrastructure Design Questions: catalog

Context: the Catalog runs as one container next to a PostgreSQL container on the one Linux server with Docker (decided earlier). Most details follow from the approved targets: a 10-connection pool, a 100 GB database volume, restart on failure, previous images kept, secrets from files, logs to standard output, and a health check. Two choices are yours and are reused for every server unit.

My defaults (not questions): the Catalog container gets a memory limit of 1 GB and half a processor core as a reservation; the database container gets 4 GB of memory; both restart on failure; the database starts first; all traffic between them stays on an internal Docker network.

## Q1. How many copies of the system should exist?

Why we ask: the organisation's way of working deploys on merge to a staging environment and gates production on manual approval (org.md). For this server stack the choice affects how many Compose stacks, databases and volumes must be hosted.

- Option A, one production stack on the server. Developers run the stack on their own machines with the stand-in for Artifactory; every change is tried there and in CI, and production is upgraded by hand with the documented upgrade-and-return steps. Pros: least to host; matches one server. Cons: no shared place to try a release before production.
- Option B, production plus a staging stack on the same server (separate Compose project, ports, volumes and database). Pros: a release is tried on the real server before production. Cons: doubles disk and memory use; staging has no real Artifactory unless one is lent.
- Option C, staging on a separate server. Pros: no competition for resources. Cons: a second server the scope does not include.
- Recommendation: A, with B possible later because the Compose file is written to be started under a different project name.

A. Option A: production only; developers use their own machines and the stand-in
B. Option B: production plus staging on the same server
C. Option C: staging on a separate server
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. Where should alerts go?

Why we ask: the alert conditions are written (for example ready check failing for 5 minutes). Someone must receive them. The organisation already has central logging and monitoring (outside these containers).

- Option A, the existing central monitoring: this design defines the metrics, conditions and severities, and the monitoring team routes them (email, chat, ticket) as it already does for other services. Pros: no new alert path; the monitoring team's rules apply. Cons: depends on that team's time to set them up.
- Option B, a small alert sender in the stack that emails the owners directly. Pros: independent of the central team. Cons: a new component to host and maintain; needs a mail server address; duplicates what the central monitoring does.
- Recommendation: A.

A. Option A: the existing central monitoring routes them
B. Option B: a sender in our stack emails the owners
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A
