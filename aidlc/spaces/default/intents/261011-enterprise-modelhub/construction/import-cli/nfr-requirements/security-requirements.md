# Security Requirements: import-cli

The CLI holds a person's personal token; the token is the main secret.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR5.1 | The token is saved only by login, in a file readable only by its owner; it cannot be given as a command-line option. | Permissions checked by a test on Linux; on Windows the file lies in the person's own profile folder | NFR5b, rule BR1.1 |
| NFR5.2 | The token never appears in output, logs, reports, error messages or the run record. | A test greps all outputs for the token | NFR5b, rule BR1.2 |
| NFR5.3 | The server address must be https, except localhost for tests. | A test refuses http to another host | NFR5, rule BR1.1 |
| NFR5.4 | The certificate of the server is verified with the computer's trusted certificates; a failure is not retried and is not bypassed. | No option to turn verification off | NFR5 |
| NFR5.5 | The CLI verifies a bundle (trusted key, every piece) before sending anything. | Existing verify code; a test with a tampered piece | NFR5, rule BR1.4 |
| NFR5.6 | No other connection is made. | Only the configured server | NFR8 |
