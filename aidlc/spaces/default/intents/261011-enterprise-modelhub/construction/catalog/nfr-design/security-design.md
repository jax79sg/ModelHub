# Security Design: catalog

How the Catalog enforces who may call what and protects tokens and documents.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR5.1 | Common request guard plus a per-route identity check | The shared guard checks the token; each route declares whether it needs a person or the import service's identity (client modelhub-artifactory-service), and a table-driven test calls every route with every kind of caller. |
| NFR5.2 | HMAC-SHA-256 with a secret pepper | The token value is 256 random bits from the operating system's generator with a recognisable prefix; only its keyed hash is stored; comparison uses a constant-time check; the pepper comes from the secret file; the value is returned once. |
| NFR5.3 | Database roles | The Catalog's database user owns its schema, is not a superuser, and is granted insert and select only on the import-record table; the migration role is separate from the runtime role. |
| NFR5.4 | Document serving headers | Unsafe types become octet-stream; every document answer carries attachment, nosniff and a sandbox policy (rule BR1.11). |
| NFR5.5 | Secrets from files | The database password and the pepper are read by the shared loader and never logged. |
| NFR5.6 | Validation at the edge | Request models check sizes, hex strings, names, paths, page sizes and search length before any query (rules BR1.4, BR1.8, BR1.9). |
| NFR5.7 | Parameterised queries only | All SQL uses bound parameters; the sort field is chosen from a fixed list, never from text. |
| NFR5.8 | Accepted limit | The trail is ordinary rows; the role grant above is the only protection; stated for the record. |
