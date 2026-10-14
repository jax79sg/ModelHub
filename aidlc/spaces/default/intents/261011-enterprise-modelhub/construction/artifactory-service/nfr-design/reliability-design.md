# Reliability Design: artifactory-service

How an import can stop at any moment and be repeated safely (no circuit breaker: NFR design question 1 A).

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR4.2, NFR4.3 | Idempotent steps and start-up sweep | Create, piece, start, plan decision, upload check and record are each safe to repeat; at start-up jobs that were verifying, uploading or recording are marked failed as interrupted (retryable), their working files removed and locks released; the CLI's rerun is decided afresh. |
| NFR4.4 | Plan decided from facts | The listing and the Catalog lookup decide skip, finish, repair or full at every create; an upload is never started for a version Artifactory holds in full. |
| NFR4.5 | Retry helper with the five timed waits | One helper applies 1, 2, 4, 8 and 16 seconds plus up to 1 second of random wait to network errors and timeouts; refusals are not retried; there is no circuit breaker. |
| NFR4.6 | Two-step removal with recorded outcome | Decision stored first; Artifactory delete (404 counts as gone); Catalog mark; outcomes failed, files_deleted_not_marked or done are stored so a repeat resumes at the right step. |
| NFR3.1, NFR3.2 | Restart policy, previous image, degraded ready | Restarts on failure; previous image tag kept; if Artifactory or the Catalog is down the ready answer says degraded, imports fail retryably, and the service stays up. |
