# Reliability Requirements: artifactory-stand-in

It only has to be dependable for the length of a test, and to fail on request.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR4.1 | The stand-in can be told to fail in the ways the contract lists, on chosen calls. | Every failure kind in rule BR1.10 has a test | NFR4, FDQ4 A |
| NFR4.2 | A version is visible only after its commit; a stopped upload leaves it partial and invisible. | Tested by cutting a transfer | NFR4, rule BR1.5 |
| NFR3.1 | No availability promise; it lives for one test run. | None | NFR3 |
