# Scalability Requirements: artifactory-service

Sized for bundles up to 200 GB and two imports at once (NFR questions Q1 A).

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR7.4 | Bundles up to 200 GB are supported. | Disk check refuses an import that does not fit, with a retryable 507 (rule BR1.20) | NFR7, NFR questions Q1 A |
| NFR7.5 | At most 2 imports run at once; a third waits for a free place. | max_running_imports = 2, a setting | NFR7, rule BR1.10 |
| NFR7.6 | Working disk for receiving and unpacking. | At least 2 x (200 GB + 10%) = 440 GB free, planned at 500 GB | NFR7 |
| NFR7.7 | Up to 20 people use the retention and key screens and import status at once. | Short calls stay within NFR2.1 | NFR7, NFR questions Q2 A |
| NFR7.8 | One copy of the service; the lock and job state are in its database schema, so a restart does not forget them. | No in-memory-only state that matters | NFR7 |
