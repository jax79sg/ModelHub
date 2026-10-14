# Monitoring Design: catalog

Metrics are taken from the Catalog's logs and its ready check by the existing central monitoring, which also routes the alerts (infrastructure question 2 A). This design defines the metrics, conditions and severities.

## Metrics And KPIs

| Metric | Source | Threshold | Why it matters |
|---|---|---|---|
| Ready check status | GET /readyz | 503 for more than 5 minutes in business hours | The Catalog cannot serve (NFR3.1) |
| Request error share | 5xx access-log lines | Over 5% for 10 minutes | Users see failures (NFR6.3) |
| List latency | duration field of /models lines | 95th percentile over 800 ms for 10 minutes | Below the 1-second target (NFR2.1) |
| Store failures | event store_failed | Any in business hours | An import could not be recorded |
| Database volume free space | ready answer warning | Under 20% free | Documents are growing (NFR7.2) |
| Connection pool wait | log of waits over 1 second | More than 10 in 10 minutes | The pool is too small for the load |

## Alerts

| Alert | Condition | Severity | Routes to |
|---|---|---|---|
| Catalog not ready | Ready 503 for over 5 minutes in business hours | High | Central monitoring, as it routes |
| High error share | 5xx over 5% for 10 minutes | High | Central monitoring |
| Slow list | p95 over 800 ms for 10 minutes | Medium | Central monitoring |
| Store failed | store_failed event | Medium | Central monitoring |
| Volume nearly full | Under 20% free | Medium | Central monitoring |

## SLIs And SLOs

| SLI | SLO target | Measurement window |
|---|---|---|
| Models list requests answered in under 1 second | At least 95% | Rolling 30 days, measured on the server |
| Successful (non-5xx) requests | At least 99% in business hours | Rolling 30 days |
| Stores that commit or roll back cleanly | 100% (no half-recorded version) | Every store |

## Logs And Tracing

Structured JSON lines on standard output are collected by the existing central logging; one access line per request and fixed event codes (store_failed, record_conflict, token_made, token_revoked, version_removed, migration_applied). No tokens, values or document content are logged. The request id travels from the portal and the import service through every Catalog line, which gives tracing across the services without a separate tracing product. Dashboard (built by the monitoring team): ready status, request rate, 5xx share, list latency percentiles, store events, volume space.
