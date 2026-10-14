# Performance Requirements: artifactory-stand-in

Targets for the test-only imitation of Artifactory (never delivered). Measured on a typical build machine. IDs continue the inception requirement they come from.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR9.1 | The stand-in starts and answers its first call quickly. | Under 2 seconds from start to first answer | NFR9 |
| NFR9.2 | Any call that does not move file content is answered quickly. | Under 50 ms at the 95th percentile | NFR9 |
| NFR9.3 | A declared (virtual) file of any size is accepted without reading or storing its content beyond the checksum stream. | Memory stays under 500 MB while accepting a 1 TiB declaration | NFR7, rule BR1.9 |
