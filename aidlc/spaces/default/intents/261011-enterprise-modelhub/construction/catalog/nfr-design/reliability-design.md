# Reliability Design: catalog

How it keeps stores all-or-nothing and survives a database outage.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR4.2 | All-or-nothing transaction | The store is one database transaction; any failure rolls back; the repeat check makes a retry safe. |
| NFR4.3 | Connection loss handling | The pool reconnects with growing waits (1, 2, 4, 8, 16 seconds, then every 30); requests answer 503 meanwhile; the ready check shows the database down; the service does not exit. |
| NFR4.4 | Graceful stop | On stop signal the service stops taking requests, waits up to 30 seconds for stores in progress, then rolls back the rest. |
| NFR4.5 | Locked migrations | Start-up takes a database advisory lock, applies pending numbered steps in order, records each, and refuses a database holding a step it does not know. |
| NFR3.1, NFR3.2 | Restart policy and previous image | The container restarts on failure; the previous image tag is kept; a documented return step re-starts it. |
| NFR3.3 | Data on a volume | The database's data directory is a named volume that survives container restarts and image upgrades (decided in the platform unit). |
