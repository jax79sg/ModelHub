# Security Requirements: artifactory-service

This unit holds the only Artifactory credential and decides what is trusted.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR5.1 | Import calls need a valid personal import token, checked with the Catalog; retention and key calls need the administrator role. | A test calls every route with no token, a personal token, a person's token and an administrator's token (rule BR1.1) | NFR5a, rule BR1.1 |
| NFR5.2 | The Artifactory credential is read from a secret file, used only inside the Artifactory gateway, and never appears in logs, messages, the command line of the upload tool or environment dumps. | A test searches logs and process listings for it | NFR5b, rule BR1.19 |
| NFR5.3 | Bundles are trusted only if signed by a key in the trusted-key list; a key is added only when the typed fingerprint matches. | Tested with a wrong key, a revoked key and a mismatched fingerprint | NFR5, rules BR1.2, BR1.13 |
| NFR5.4 | Every file is checked against the signed manifest before upload; a difference stops the import. | A test alters one byte in a piece and in an unpacked file | NFR5, rule BR1.6 |
| NFR5.5 | Received data is stored in a working folder the service owns, with owner-only permissions, and removed when the import ends. | A test finds no leftover files after done, failed, cancelled and restart | NFR5, rules BR1.6, BR1.11 |
| NFR5.6 | Nothing is deleted in Artifactory without an administrator's decision for that version. | No bulk call exists; a test tries to remove without a decision | NFR5, rules BR1.16, BR1.17 |
| NFR5.7 | The service's database user reaches only its own schema. | A test tries to read the Catalog's tables and is refused | NFR5, rule BR1.21 |
| NFR5.8 | Paths in unpacked bundles cannot escape the working folder. | Entries with '..', absolute paths or links are refused | NFR5, rule BR1.6 |
| NFR5.9 | Only the sizes and names the signed description allows are accepted for pieces. | Oversized pieces are refused with 413 (rule BR1.4) | NFR5, rule BR1.4 |
