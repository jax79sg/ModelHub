# Observability Requirements: artifactory-stand-in

What a test can read afterwards.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR6.1 | Logs use the shared log shape (JSON lines on standard output). | Fields as contract C7 | NFR6 |
| NFR6.2 | A test can read every call made: sequence, method, path, status, time and the failure switch that fired. | Recorded calls readable until the stand-in stops | NFR6, rule BR1.11 |
| NFR6.3 | A test can read the assumption register and the checklist. | Produced from the register; a test fails if a behaviour has no entry | FR7.2, FR7.3, rule BR1.13 |
