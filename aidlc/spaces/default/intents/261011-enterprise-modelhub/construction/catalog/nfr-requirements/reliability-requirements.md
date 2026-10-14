# Reliability Requirements: catalog

Recovery in 4 business hours (NFR questions Q1 A). Backup was left for a later phase in the scope.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR3.1 | Available in business hours; no uptime percentage is promised. | Planned downtime for upgrades is allowed | NFR3 |
| NFR3.2 | Back within 4 business hours of a failure being noticed, by restarting the container or returning to the previous version. | The upgrade-and-return procedure is rehearsed once (FR6.6) | NFR3, NFR questions Q1 A |
| NFR3.3 | The database's data survives a container restart and an image upgrade. | Kept on a volume (FR6.3); a test restarts and finds the data | NFR3, FR6.3 |
| NFR4.2 | A store is all or nothing, and a repeat is safe. | Tested by failing the database midway (AC2.1) | NFR4, rules BR1.1, BR1.2 |
| NFR4.3 | If the database is unreachable the service stays up, answers 503, retries its connection with growing waits and reports ready 503. | No crash; recovers by itself when the database returns | NFR4 |
| NFR4.4 | A stop finishes in-flight stores or rolls them back. | Up to 30 seconds' grace, then rollback | NFR4 |
| NFR4.5 | Database upgrade steps run under a lock and keep data; an unknown newer database stops the start. | Tested with two copies starting together | NFR4, rule BR1.21 |
