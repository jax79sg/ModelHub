# Entities: common

Inputs: `unit-of-work.md` (U1), `requirements.md` (FR3.1, FR6.4, FR6.5, NFR5), contracts C6 and C7, and the answers in `functional-design-questions.md` (written FDQ). `common` stores nothing on disk and has no database. These are the things its code holds in memory while a service runs.

```yaml
unit: common
entities:
  - name: KeySet
    description: The Keycloak signing keys the library currently trusts to check token signatures.
    attributes:
      - {name: keys, type: list of key, required: true, constraints: "each has key id, algorithm (RS256 or ES256) and public key"}
      - {name: fetched_at, type: UTC time, required: false, constraints: "empty until the first successful fetch"}
      - {name: last_refresh_attempt_at, type: UTC time, required: false, constraints: "used to limit refreshes to one per 60 seconds (BR1.4)"}
      - {name: state, type: text, required: true, allowed: [empty, loaded, stale], default: empty, constraints: "stale means the last refresh failed; keys are still used (BR1.4)"}
    relationships:
      - {to: TokenVerdict, cardinality: "1..*", direction: used-by}
  - name: TokenVerdict
    description: The result of checking one token. Created per request, never stored.
    attributes:
      - {name: valid, type: boolean, required: true}
      - {name: reason, type: text, required: true, allowed: [ok, missing, malformed, bad_signature, unknown_key, expired, not_yet_valid, wrong_issuer, wrong_audience, missing_claim, bad_algorithm], constraints: "ok exactly when valid (BR1.2)"}
      - {name: person_id, type: text, required: false, constraints: "the token's sub; set only when valid"}
      - {name: person_name, type: text, required: false, constraints: "preferred_username; set only when valid"}
      - {name: is_admin, type: boolean, required: true, default: false, constraints: "BR1.3"}
    relationships:
      - {to: KeySet, cardinality: "*..1", direction: uses}
  - name: Settings
    description: The non-secret configuration of a service, read from environment variables with documented names.
    attributes:
      - {name: name, type: text, required: true, unique: true, constraints: "starts with MODELHUB_"}
      - {name: type, type: text, required: true, allowed: [text, whole number, number, boolean, address, list]}
      - {name: default, type: text, required: false}
      - {name: required, type: boolean, required: true}
    constraints:
      - "the library defines the shared names (realm address, client id, secrets folder, log level, timeouts); each service adds its own"
  - name: Secret
    description: One secret read from a file. The value is wrapped so it cannot be printed.
    attributes:
      - {name: name, type: text, required: true, unique: true, allowed: [database_password, keycloak_client_secret, artifactory_token, token_hash_pepper], constraints: "names from contract C7"}
      - {name: value, type: secret text, required: true, constraints: "never in a log, an error message, a string conversion or a health answer (BR1.6, BR1.8)"}
    relationships:
      - {to: LogRecord, cardinality: "1..*", direction: redacted-from}
  - name: LogRecord
    description: One line of structured log written to standard output.
    attributes:
      - {name: ts, type: UTC time, required: true}
      - {name: level, type: text, required: true, allowed: [debug, info, warning, error]}
      - {name: service, type: text, required: true}
      - {name: event, type: text, required: true, constraints: "a short fixed code, not free text"}
      - {name: requestId, type: text, required: false, constraints: "BR1.9"}
      - {name: person, type: text, required: false, constraints: "user name only, never a token"}
      - {name: message, type: text, required: false, constraints: "after redaction (BR1.8)"}
  - name: HealthCheck
    description: One check a service registers for the ready answer.
    attributes:
      - {name: name, type: text, required: true, unique: true, allowed: [database, keycloak, artifactory]}
      - {name: critical, type: boolean, required: true, constraints: "decided by the service; critical down means 503 (BR1.11)"}
      - {name: last_result, type: text, required: true, allowed: [ok, down, unknown], default: unknown}
      - {name: last_checked_at, type: UTC time, required: false}
      - {name: timeout_seconds, type: number, required: true, default: 2}
      - {name: cache_seconds, type: number, required: true, default: 10}
    relationships:
      - {to: ReadyReport, cardinality: "*..1", direction: feeds}
  - name: ReadyReport
    description: The answer to GET /readyz, built from the checks.
    attributes:
      - {name: status, type: text, required: true, allowed: [ok, degraded, down]}
      - {name: checks, type: map of name to ok or down, required: true}
      - {name: http_status, type: whole number, required: true, allowed: [200, 503]}
```

## Summary

Seven entities. `KeySet` and `TokenVerdict` cover the token check (FR3.1). `Settings` and `Secret` cover configuration and secrets (FR6.4). `LogRecord`, `HealthCheck` and `ReadyReport` cover logging and health (FR6.5). None is written to disk; the secret files and environment variables are read once at start-up (FDQ2 A).
