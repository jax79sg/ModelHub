# Performance Requirements: import-cli

Targets for the import command on an import computer.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR7.1 | Memory stays at or below 8 GB at peak for any file size. | Files and pieces are read in blocks of at most 8 MiB; tested with a 200 GB declared piece set | NFR7 |
| NFR7.2 | The command can use the link fully for one piece at a time. | At least 90% of the measured link speed on a 1 Gbit/s link to the stand-in | NFR7, functional design FDQ3 A |
| NFR1.1 | The command reports a finished import promptly after the service says done. | Within 2 seconds of the service's done | NFR1 |
| NFR4.1 | A rerun after a stop sends only the pieces the service lacks. | No piece already stored is sent again | NFR4 |
