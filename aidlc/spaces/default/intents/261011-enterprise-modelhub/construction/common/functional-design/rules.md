# Rules: common

The decisions the shared library makes. Sources are requirement and contract IDs plus the answers in `functional-design-questions.md` (FDQ). Token claims are contract C6; log, secret and health conventions are contract C7.

```yaml
unit: common
rules:
  - id: BR1.1
    statement: A token is accepted only if its signature, signing method, issuer, audience, expiry and required claims are all correct.
    category: authorization
    applies_to: [TokenVerdict, KeySet]
    trigger: any request that needs a signed-in person
    logic: "IF the token is absent THEN reason missing. IF it is not a three-part signed token THEN malformed. IF its signing method is not RS256 or ES256 (including none and any shared-secret method) THEN bad_algorithm. IF no known key matches its key id THEN unknown_key. IF the signature does not verify THEN bad_signature. IF iss differs from the configured realm address THEN wrong_issuer. IF aud does not include the configured client id THEN wrong_audience. IF exp is more than 60 seconds past THEN expired. IF nbf is present and more than 60 seconds ahead THEN not_yet_valid. IF sub or preferred_username is missing THEN missing_claim. Otherwise valid, reason ok."
    violation: the request is refused with 401 (BR1.2)
    source: [FR3.1, NFR5a, C6]
  - id: BR1.2
    statement: A refused token gets the same minimal answer every time, and the reason goes only to the log as a fixed code.
    category: policy
    applies_to: [TokenVerdict, LogRecord]
    trigger: a verdict with valid false
    logic: "Answer HTTP 401 with code token_invalid and no detail. Write one log line with event token_rejected and the reason code. Never write any part of the token, its claims or the Authorization header."
    violation: not applicable
    source: [FR3.1, NFR5b, C6 failure, FDQ4 A]
  - id: BR1.3
    statement: A person is an administrator only if the token's realm roles contain modelhub-admin; an action that needs it, without it, is refused with 403.
    category: authorization
    applies_to: [TokenVerdict]
    trigger: a valid token on an action that needs administrator rights
    logic: "is_admin is true exactly when realm_access.roles includes the text modelhub-admin; a missing realm_access claim means false. IF the action needs administrator rights AND is_admin is false THEN answer 403 with code forbidden and log event forbidden with the person's name."
    violation: the 403 answer
    source: [FR4.1, C6 admin]
  - id: BR1.4
    statement: The library trusts the last good set of signing keys, refreshes it when an unknown key id appears, and never goes without keys by choice.
    category: constraint
    applies_to: [KeySet]
    trigger: service start-up; a token with a key id not in the set
    logic: "At start-up fetch the keys from the realm's published key address (state loaded). IF a token carries an unknown key id AND the last refresh attempt was more than 60 seconds ago THEN try one refresh. IF a refresh fails THEN keep every key already held (state stale) and keep checking tokens against them; a token with a key id still unknown is refused as unknown_key. IF the first fetch at start-up fails THEN the set stays empty, every token is refused as unknown_key, and the ready answer is 503 until a fetch succeeds."
    violation: refusal as unknown_key
    source: [FR3.8, C6 format, FDQ1 A]
  - id: BR1.5
    statement: Every request path needs a valid token unless the service declares it open, and only the health paths are open by default.
    category: authorization
    applies_to: [TokenVerdict]
    trigger: any incoming request
    logic: "The paths /healthz and /readyz need no token. Every other path needs a valid token (BR1.1). A service may declare more open paths only by naming each one in its start-up code; there is no pattern or wildcard form."
    violation: 401 per BR1.2
    source: [FR3.1, NFR5a, AC3.1]
  - id: BR1.6
    statement: Secrets are read once at start-up from files, wrapped so they cannot be printed, and a missing or unreadable one stops the service from starting.
    category: validation
    applies_to: [Secret]
    trigger: service start-up
    logic: "Each service names the secrets it needs. For each, read the file of that name in the folder MODELHUB_SECRETS_DIR (default /run/secrets), strip one trailing newline, and wrap it. IF a file is missing, unreadable or empty THEN collect its name. After all are tried, IF any were collected THEN print one message listing the names only (never values or file contents) and exit with a failure. Secrets are not re-read while running."
    violation: the service exits at start-up
    source: [FR6.4, NFR5b, C7 secrets, FDQ2 A, FDQ3 A]
  - id: BR1.7
    statement: Settings come from environment variables with documented names, are checked at start-up, and a wrong one stops the service from starting.
    category: validation
    applies_to: [Settings]
    trigger: service start-up
    logic: "Each setting is read from its MODELHUB_ variable; absent uses the default if one exists. A required setting that is absent, or a value that is not of the stated type, is collected by name with the expected type. After all are tried, IF any were collected THEN print one message listing the names and expected types and exit with a failure. The message never includes the value."
    violation: the service exits at start-up
    source: [C7 configuration, FDQ3 A]
  - id: BR1.8
    statement: Logs are one JSON object per line on standard output, and nothing secret is ever in them.
    category: policy
    applies_to: [LogRecord, Secret]
    trigger: any log call
    logic: "Write the fields ts (UTC, ISO 8601), level, service, event, and requestId, person and message when present, as one JSON line to standard output. Any extra field whose name contains token, password, secret, pepper, authorization or cookie (any case) has its value replaced with [redacted]. Any loaded Secret value that appears inside message or any text field is replaced with [redacted]. A log level below the configured level is dropped."
    violation: not applicable
    source: [FR6.5, NFR5b, C7 logging, AC6.1]
  - id: BR1.9
    statement: Every request has a request id, kept from the caller when it is valid and made up otherwise, and returned in the answer.
    category: policy
    applies_to: [LogRecord]
    trigger: any incoming request
    logic: "IF the X-Request-Id header is present AND is 1 to 64 characters of letters, digits, hyphen and underscore THEN use it. ELSE make a new random id. Put it in every log line for the request and in the X-Request-Id answer header."
    violation: not applicable
    source: [FR6.5, C7 logging]
  - id: BR1.10
    statement: The live check answers 200 whenever the process can answer at all, and shows nothing else.
    category: policy
    applies_to: [ReadyReport]
    trigger: GET /healthz
    logic: "Answer 200 with status ok. Run no check, touch no dependency, show no setting or secret."
    violation: not applicable
    source: [FR6.5, C7 health]
  - id: BR1.11
    statement: The ready check runs the service's registered checks at most once every 10 seconds, each with a 2-second limit, and says 503 only when a critical one is down or no keys are loaded.
    category: policy
    applies_to: [HealthCheck, ReadyReport]
    trigger: GET /readyz
    logic: "For each registered check whose last result is older than 10 seconds, run it with a 2-second limit; a limit overrun or an error counts as down. Build the checks map of ok or down. IF any critical check is down, or KeySet state is empty, THEN status down and HTTP 503. ELSE IF any non-critical check is down THEN status degraded and HTTP 200. ELSE status ok and HTTP 200. The answer holds check names and results only, never messages from the dependency."
    violation: the 503 answer
    source: [FR6.5, NFR6, C7 health, FDQ5 A]
  - id: BR1.12
    statement: The library supplies the shared default timeouts so no service chooses its own.
    category: policy
    applies_to: [Settings]
    trigger: service start-up
    logic: "Provide connect 5 seconds, read 30 seconds and piece upload 600 seconds as settings with these defaults, which a service may override by environment variable but not set to zero or a negative number."
    violation: start-up fails per BR1.7
    source: [C7 timeouts_default_seconds]
```

## Rules Summary

| ID | Rule | Category |
|----|------|----------|
| BR1.1 | Token fully checked | authorization |
| BR1.2 | Minimal 401, reason in log | policy |
| BR1.3 | Administrator from the realm role | authorization |
| BR1.4 | Last good keys kept; refresh on unknown key | constraint |
| BR1.5 | Only health paths are open by default | authorization |
| BR1.6 | Secrets read once; stop if missing | validation |
| BR1.7 | Settings checked at start-up | validation |
| BR1.8 | JSON logs with redaction | policy |
| BR1.9 | Request id | policy |
| BR1.10 | Live check | policy |
| BR1.11 | Ready check | policy |
| BR1.12 | Shared default timeouts | policy |
