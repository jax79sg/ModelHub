# Technology Decisions: catalog

Choices for this unit. The shared stack (Python 3.12, FastAPI, uvicorn, psycopg 3 with plain SQL) was chosen once for all server units.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR10.1 | Runs as a Linux container with Python 3.12; the import command's platform needs are met in import-cli. | Image built on the internet side | NFR8, NFR10 |
| NFR9.1 | Python 3.12, FastAPI, uvicorn; psycopg 3 with a connection pool; plain SQL with numbered migration files run by a small runner in the service. | Chosen for reuse of the prototype and plain SQL for search | NFR9, NFR questions Q1 A |
| NFR9.2 | PostgreSQL (a current supported major version, 16 assumed) in its own container; full-text search with the English configuration and the pg_trgm extension for parts of words, both in the standard distribution. | Version to be confirmed with the organisation's database standards | FR2, rule BR1.9 |
| NFR9.3 | Keyed hash with the standard library (hmac, hashlib, secrets); multipart upload with python-multipart. | No cryptography written by us | NFR5 |
| NFR9.4 | Tests are pytest, written before the code, against a real PostgreSQL started for the test run; ruff (line length 100). | The load test for NFR2.1 is a script that fills 1,000 models and times 100 requests | NFR9, team.md |
| NFR8.1 | The service connects only to PostgreSQL and (through the shared library) to Keycloak's key address. | No other connection; none to the internet | NFR8 |
