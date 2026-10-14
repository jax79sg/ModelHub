# Security Design: artifactory-service

How the Artifactory credential, the trust list and the destructive actions are protected.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR5.1 | Two kinds of identity per route | Import routes accept only a personal import token, checked with the Catalog (cached for no more than 30 seconds so a revocation takes effect within that time); retention and key routes accept only an administrator's Keycloak token; a table-driven test calls every route with each kind. |
| NFR5.2 | Credential confined to the gateway | The Artifactory token is read once from the secret file into the gateway object, passed to the upload process through a private file descriptor or a mode-600 temporary configuration removed after the call, never on the command line or in the environment of other processes; log redaction masks it. |
| NFR5.3 | Typed-back fingerprint | The service computes the fingerprint of an offered key and compares it with the typed one before storing; revoked keys are kept as records and refused at signature checks. |
| NFR5.4 | Two checks on the bundle | The signature is checked at create; after unpacking, every file is checked against the signed manifest; both use the same code as the CLI. |
| NFR5.5 | Private working folder | Created with mode 700, owned by the service user, one subfolder per import; removed in every end state and swept at start-up. |
| NFR5.6 | Single-version destructive action | The remove route takes one model and commit, requires the administrator role and an imported version, and records the decision before acting. |
| NFR5.7 | Own schema and user | The service's database user can read and write only its own schema; creation of the schema and users is done by the platform's start-up step. |
| NFR5.8 | Safe unpacking | Entries are read through the existing safe-join check: no '..', no absolute path, no links, no entry outside the import's folder; an extra or missing file fails the manifest check. |
| NFR5.9 | Size limits from the signed description | Each piece may be no larger than its declared size; a larger body is cut off and answered 413. |
