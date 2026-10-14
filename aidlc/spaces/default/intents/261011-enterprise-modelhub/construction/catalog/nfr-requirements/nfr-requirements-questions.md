# NFR Requirements Questions: catalog

Context: "NFR" means quality targets. The inception targets already cover list speed (NFR2: under 1 second for 95% of requests at 1,000 models), capacity (NFR7: about 1,000 models, up to 10 versions each), availability in business hours with no uptime percentage (NFR3) and restart safety (NFR4). Backup was left for a later phase in the scope, so this unit states what the data volume must survive (restart and image upgrade, FR6.3) and nothing about backups. Two numbers are still missing and they are yours to give; the answers are reused by `artifactory-service` and `portal`.

My defaults for this unit (not questions): an identical repeated store answers in under 1 second; a first store of a version with 10,000 files and 100 MB of documents completes in under 60 seconds; the document store size limit is 16 MiB per document; the import trail is kept for the life of the system (no purge); database queries have a 5-second limit; logs and health as in the shared conventions.

## Q1. How quickly must the system be back after a failure?

Why we ask: NFR3 says "available in business hours" but gives no repair time. The answer sets how much care goes into restart, health checks and the upgrade-and-return procedure, and is reused for every server unit.

- Option A, back within 4 business hours of the failure being noticed, by restarting containers or returning to the previous version. Pros: realistic for one Linux server with a restart policy and the kept previous images (FR6.6). Cons: no promise outside business hours.
- Option B, back by the next business day. Pros: no extra effort. Cons: a failure at the start of the day could cost the day.
- Option C, back within 1 hour in business hours. Pros: tighter. Cons: needs people on call and probably a second server, which the scope excludes.
- Recommendation: A.

A. Option A: within 4 business hours
B. Option B: by the next business day
C. Option C: within 1 hour in business hours
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. How many people use the portal and the Catalog at the same time?

Why we ask: the list-speed target needs a load to be measured against, and the portal and Catalog must be sized for it. The recommendation is a small group, consistent with a single server.

- Option A, up to 20 people at the same time (and one or two imports). Pros: sized for a team; a single server is plenty. Cons: more later needs re-checking.
- Option B, up to 100 people at the same time. Pros: room to grow. Cons: heavier test setup and possibly more than one copy of the portal.
- Option C, up to 500 people. Pros: organisation-wide. Cons: needs a different architecture (more than one server).
- Recommendation: A.

A. Option A: up to 20 at the same time
B. Option B: up to 100 at the same time
C. Option C: up to 500 at the same time
D. Not yet defined
X. Other (please specify)

[Answer]: A
