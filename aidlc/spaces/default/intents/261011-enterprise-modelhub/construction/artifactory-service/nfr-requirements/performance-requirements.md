# Performance Requirements: artifactory-service

Targets for the container that imports and runs retention. The import-time target depends on links and a real Artifactory and is checked when one exists (NFR questions Q2 A).

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR7.1 | A 100 GB model imports end to end in under 4 hours, from the first piece sent to done, on a 1 Gbit/s link. | Measured on a real Artifactory when available; until then the stand-in measures the service's own part (receiving, unpacking, checking) | NFR7, NFR questions Q2 A |
| NFR7.2 | The service's own work (receive, join, unpack, check) keeps up with the link. | At least 100 MB/s sustained on the server's disk with SHA-256 checking, tested with the stand-in | NFR7 |
| NFR7.3 | Memory stays within the planning figure for any file size. | At most 8 GB at peak; files and pieces are streamed in blocks of at most 8 MiB | NFR7 |
| NFR1.1 | After the upload and the Catalog record, the model is findable at once; the service adds no further delay. | The record is sent as soon as Artifactory's listing matches | NFR1 |
| NFR2.1 | Short calls (create, progress, key list, retention list) answer quickly. | 95th percentile under 1 second, excluding the Artifactory listing; the listing is bounded by the 30-second read limit | NFR2 |
| NFR4.1 | A piece is acknowledged promptly. | Overhead beyond the transfer under 100 ms per piece | NFR4 |
