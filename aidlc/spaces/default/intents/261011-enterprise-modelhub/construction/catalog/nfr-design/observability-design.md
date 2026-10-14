# Observability Design: catalog

What the central logging and monitoring can read.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR6.1 | Access line per request | The shared log formatter writes request id, person name, method, path, status and duration; document bytes and token values are never logged. |
| NFR6.2 | Health with a critical database check | The database check runs a trivial query with a 2-second limit; ready is 503 when it fails. |
| NFR6.3 | Measures taken from logs | Health: the ready answer; error rate: share of 5xx lines; latency: duration field. |
| NFR6.4 | Alert thresholds below harm | Ready 503 over 5 minutes in business hours; 5xx over 5% for 10 minutes; list p95 over 800 ms for 10 minutes; volume free space under 20%. |
| NFR6.5 | Fixed event codes | store_failed, record_conflict, token_made, token_revoked, version_removed, migration_applied are logged with the person and ids, never values. |
