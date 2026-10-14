# Security Requirements: catalog

What the Catalog must enforce. It is the only holder of model information, the trail and the personal tokens.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR5.1 | Every call needs a valid Keycloak token; writes, removal, retention listing and token checking need the import service's identity. | A test calls every route without a token, with a person's token and with the service token (rule BR1.14) | NFR5a, rule BR1.14 |
| NFR5.2 | Personal token values are stored only as a keyed hash (HMAC-SHA-256) with a secret pepper; values are never logged or listed. | A test searches the database dump and logs for a made token's value | NFR5b, rules BR1.15, BR1.16 |
| NFR5.3 | The database user can reach only the Catalog's own schema, is not a superuser, and has no right to update or delete import-trail rows. | A test tries both and is refused | NFR5c, rule BR1.13 |
| NFR5.4 | Documents are served as data: unsafe types come as octet-stream, with attachment, nosniff and a sandbox policy. | A test fetches an html and an svg document and checks the headers | NFR5, rule BR1.11 |
| NFR5.5 | Secrets (database password, token pepper) come from the server's secret files only. | None in images, project files, logs or errors (shared library) | NFR5b |
| NFR5.6 | Inputs are validated at the edge: sizes, hex strings, names, paths, page sizes and search length. | A test per rule BR1.4 and BR1.8 fault | NFR5, rules BR1.4, BR1.8, BR1.9 |
| NFR5.7 | Queries use parameters only; no query text is built from input. | A review check and a test with hostile text in every filter | NFR5 |
| NFR5.8 | The import trail is ordinary rows and is not tamper-proof; this is an accepted limit. | Stated for the record | NFR5c |
