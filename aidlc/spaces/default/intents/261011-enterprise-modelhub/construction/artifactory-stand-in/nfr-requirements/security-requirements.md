# Security Requirements: artifactory-stand-in

The stand-in holds no real secret and is never part of what is delivered; these rules keep it from becoming a way in.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR5.1 | The stand-in listens only on the local machine. | Binds 127.0.0.1; refuses to start otherwise (rule BR1.14) | NFR5 |
| NFR5.2 | Calls need the one token the test sets; wrong or missing gives 401, no write permission gives 403. | Tested for each call group | NFR5, rule BR1.1 |
| NFR5.3 | The token and file content are never written to the call record or to logs. | A test searches the record and logs for the token | NFR5b, rule BR1.11 |
| NFR5.4 | Uploaded paths cannot escape the version's folder. | Paths with '..', absolute or backslash are refused with 400 | NFR5, rule BR1.15 |
| NFR5.5 | The stand-in is not included in any delivered image or program. | A platform check fails if it is found in an image | NFR9, rule BR1.14 |
| NFR5.6 | The stand-in never reads real credentials from the environment. | Token is supplied only by the test | NFR5, rule BR1.14 |
