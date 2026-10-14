# Scalability Requirements: artifactory-stand-in

How much the stand-in must hold during a test run.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR7.1 | Holds the versions a test creates. | At least 1,000 stored versions of up to 10,000 files each in one run | NFR7 |
| NFR7.2 | Accepts several uploads at the same time. | At least 8 concurrent uploads, each to a different version, with no mix-up | NFR7, NFR4 |
