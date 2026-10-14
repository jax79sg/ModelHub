# Technology Decisions: common

Choices for the shared library. The server stack (Python 3.12 images, FastAPI, psycopg 3 with plain SQL) was chosen once for all server units in the stand-in questions.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR10.1 | Supports Python 3.10 and later; the images use 3.12. | Existing CI covers 3.10 and 3.12 | NFR10, NFR questions Q2 B |
| NFR5.10 | PyJWT with the cryptography package checks token signatures; the key-set (JWKS) fetching is written in the library. | Algorithm list set explicitly to RS256 and ES256 | NFR5, NFR questions Q1 A |
| NFR6.1 | Logging uses the standard library's logging with a JSON formatter we write; no logging framework is added. | One JSON object per line on standard output | NFR6 |
| NFR9.1 | Tests use pytest, written before the code; ruff for checks and format (line length 100). | Team practice | NFR9, team.md |
| NFR8.1 | The library makes no connection except to the realm's key address named in settings. | A test blocks other sockets | NFR8 |
| NFR5.11 | Dependencies kept minimal and pinned to ranges; the build lists them for scanning. | Dependabot and code scanning stay on | NFR5 |
