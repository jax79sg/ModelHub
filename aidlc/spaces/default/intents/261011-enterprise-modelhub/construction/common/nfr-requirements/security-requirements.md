# Security Requirements: common

The shared library is the most security-sensitive code in the system: every server unit trusts its token check, secret handling and redaction.

| ID | Requirement | Measure | Source |
|----|-------------|---------|--------|
| NFR5.1 | Only tokens signed with RS256 or ES256 by a known key are accepted; none, shared-secret methods and unknown key ids are refused. | Tests for expired, tampered, wrong-issuer, wrong-audience, wrong-algorithm and unknown-key tokens (rule BR1.1) | NFR5a, rule BR1.1 |
| NFR5.2 | Every path needs a valid token except the health paths and any path a service names explicitly. | No wildcard form; a test lists the open paths of each service | NFR5a, rule BR1.5 |
| NFR5.3 | A refused token gets the same minimal answer; the reason is only a fixed code in the log. | No part of a token in any log line | NFR5b, rule BR1.2 |
| NFR5.4 | Secrets are read from files once at start-up, wrapped so they cannot be printed, and never appear in logs, errors or health answers. | A test prints, logs and serialises a secret and finds it nowhere | NFR5b, rules BR1.6, BR1.8 |
| NFR5.5 | Log fields whose names suggest a secret, and any loaded secret value inside text, are redacted. | Tested with each field name pattern | NFR5b, rule BR1.8 |
| NFR5.6 | A missing or unreadable secret or setting stops the service at start-up, naming the item only. | Tested with each secret absent | NFR5b, rules BR1.6, BR1.7 |
| NFR5.7 | Key fetching is limited so a stream of unknown key ids cannot hammer Keycloak. | At most one refresh per 60 seconds | NFR5, rule BR1.4 |
| NFR5.8 | Clock difference allowed on token times. | 60 seconds | NFR5, rule BR1.1 |
| NFR5.9 | Token checking adds little time per request. | Under 5 ms with a cached key | NFR5 |
