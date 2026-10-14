# NFR Design Questions: artifactory-service

Context: most of this unit's resilience follows from the approved import rules and targets: five timed retries for network errors, the restart handling that marks interrupted imports failed, a per-model lock, a limit of two running imports, a disk check before receiving, progress written to the database every 5 seconds, and a start-up sweep that removes working folders that belong to no live import. One choice has a real alternative.

## Q1. Should the service stop calling Artifactory or the Catalog for a while after repeated failures (a circuit breaker)?

Why we ask: if Artifactory is down, every import would spend its five retries (31 seconds plus jitter) on each call and still fail. A breaker would make later calls fail at once for a while.

- Option A, no breaker: each call does its own five timed retries. Pros: simple; behaviour matches the rules and the CLI's own retries; imports are few and long, so the extra waits are small. Cons: during an outage each import attempt waits about half a minute before failing.
- Option B, a breaker: after 5 failures in a row the service refuses new imports and retention actions for 60 seconds with a retryable answer, then tries one call. Pros: fails fast and spares Artifactory during an outage. Cons: more states to test; a wrongly tripped breaker blocks work.
- Recommendation: A.

A. Option A: no breaker
B. Option B: a breaker (5 failures, 60 seconds)
C. Let the design decide
D. Not yet defined
X. Other (please specify)

[Answer]: A
