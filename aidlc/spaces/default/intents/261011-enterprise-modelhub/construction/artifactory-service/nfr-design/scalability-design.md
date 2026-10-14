# Scalability Design: artifactory-service

Sizing for two imports at once and bundles up to 200 GB.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR7.4 | Disk check at create | Free space on the working volume must be at least the bundle size plus 10% for this import and the reserve for running imports; otherwise 507, retryable. |
| NFR7.5 | Counting semaphore for running imports | At most 2 jobs in verifying, uploading or recording; a third start is answered service_busy and waits in receiving. |
| NFR7.6 | Working volume of 500 GB | Planned separately from the database volume; the ready answer warns below 25% free. |
| NFR7.7 | Short calls stay light | Retention and key screens read small tables with paging. |
| NFR7.8 | State in the database | Job, lock and piece rows are in the service's schema, so a restart loses nothing; one copy runs. |
