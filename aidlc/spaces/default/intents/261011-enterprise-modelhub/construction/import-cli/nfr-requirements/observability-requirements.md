# Observability Requirements: import-cli

What the person and an operator can see.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR6.1 | Live progress for any step over 2 seconds, plain lines every 10 seconds when not on a terminal. | Rule BR1.10 | NFR6 |
| NFR6.2 | A final report lists each model with its result and reason, with counts and exit status. | Rule BR1.9 | NFR6 |
| NFR6.3 | The existing run record keeps a line per model without secrets. | A test checks the record | NFR6 |
