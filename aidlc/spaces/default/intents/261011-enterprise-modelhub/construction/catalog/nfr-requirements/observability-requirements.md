# Observability Requirements: catalog

What the central logging and monitoring can read.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR6.1 | Structured JSON logs on standard output, one access line per request with request id, person name, method, path, status and duration. | Shared log shape (contract C7); never a token, value or document content | NFR6 |
| NFR6.2 | A live check and a ready check; the database is critical. | GET /healthz and /readyz; ready 503 when the database is down | NFR6, FR6.5 |
| NFR6.3 | One health metric and one error-rate measure can be taken from the logs and health. | Health: the ready check; error rate: share of 5xx access lines | NFR6 |
| NFR6.4 | Alerts are set below the point of harm. | Ready 503 for over 5 minutes in business hours; 5xx share over 5% for 10 minutes; list p95 over 800 ms for 10 minutes | NFR6 |
| NFR6.5 | Events worth an operator's eye are logged with fixed codes. | store_failed, record_conflict, token_made, token_revoked, version_removed, migration_applied | NFR6 |
