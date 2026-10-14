# Reliability Requirements: artifactory-service

Restart safety is the main promise: an import stopped at any moment and run again gives a correct, complete result.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR4.2 | Stopping an import at any moment and running it again gives a correct, complete result. | A test stops the service at each state of the import and reruns; no half-finished record is treated as complete | NFR4, rules BR1.3, BR1.11 |
| NFR4.3 | At start-up every import that was running is marked failed as interrupted, retryable, and its working files removed. | Tested by killing the service mid-upload | NFR4, rule BR1.11 |
| NFR4.4 | The Artifactory upload is never repeated for a version Artifactory already holds in full. | Repeat gives plan 'finish' or 'skip' | NFR4, rule BR1.3 |
| NFR4.5 | Network errors are retried five times at 1, 2, 4, 8 and 16 seconds with a little random wait; other errors are not retried. | Tested with the stand-in's failure switches | NFR4, rule BR1.7 |
| NFR4.6 | A retention removal that fails at either step leaves the version listed and can be repeated. | Tested for each failing step | NFR4, rule BR1.17 |
| NFR3.1 | Available in business hours; back within 4 business hours of a failure noticed. | Restart policy on failure; previous image kept | NFR3 |
| NFR3.2 | If Artifactory or the Catalog is unreachable the service stays up, imports fail with a retryable reason, and the ready check reports it. | No crash; recovers when they return | NFR3, NFR4 |
