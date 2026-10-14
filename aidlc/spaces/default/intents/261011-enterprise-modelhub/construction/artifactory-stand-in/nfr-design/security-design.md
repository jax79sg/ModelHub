# Security Design: artifactory-stand-in

How it stays harmless: local only, token required, nothing secret recorded, never delivered.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR5.1 | Local bind check at start | The server binds 127.0.0.1 only and refuses to start if asked for another address (rule BR1.14). |
| NFR5.2, NFR5.6 | Token given by the test only | One bearer token is a start-up argument of the test fixture; the stand-in never reads the environment or files for credentials; wrong or missing gives 401 and no write permission gives 403 (rule BR1.1). |
| NFR5.3 | Call record without secrets or bodies | The record stores sequence, method, path, status, time and the failure switch only; the Authorization header and request bodies are never kept (rule BR1.11). |
| NFR5.4 | Path check before any write | Every incoming path is checked for empty, absolute, '..', backslash and drive letter before it is used, and the folder of a version is resolved and checked to lie inside the temporary folder (rule BR1.15). |
| NFR5.5 | Kept out of delivered files | The stand-in lives in the test tree, not the package; a platform check fails if an image or the single-file program contains it. |
