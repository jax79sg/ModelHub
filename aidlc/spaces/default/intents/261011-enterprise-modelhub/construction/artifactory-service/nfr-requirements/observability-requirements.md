# Observability Requirements: artifactory-service

What operators and the central monitoring can read.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR6.1 | Structured JSON logs on standard output; one line per request with request id, person, method, path, status, duration; and one line per import state change with import id, model, step and bytes. | Shared log shape; no secrets, no token, no raw Artifactory output | NFR6 |
| NFR6.2 | Live and ready checks; the database is critical; Artifactory and the Catalog are reported but not critical for the ready answer. | GET /healthz and /readyz; degraded when either is down | NFR6, FR6.5 |
| NFR6.3 | Operators can see import progress and failure reasons. | Import state and error codes in logs and through the import call | NFR6 |
| NFR6.4 | Alerts set below the point of harm. | Ready 503 over 5 minutes; imports failed as 'interrupted' or 'artifactory_inconsistent' (any); working disk free under 25%; Artifactory down over 10 minutes | NFR6 |
| NFR6.5 | Events logged with fixed codes. | import_created, import_skipped, import_done, import_failed, key_added, key_revoked, retention_decided, version_removed | NFR6 |
